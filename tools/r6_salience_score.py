"""R6: score the salience ranking against the annotation's `significant` flag.

    .\\dev.ps1
    python tools/r6_salience_score.py

Reports AUC, P@10, P@20 and MAP at the three annotated chapters, beside v1's
degree-based figures from R0/R1. The ranking is READ, never fitted: the features and
their equal weights were fixed in the R6 pre-registration before this ran.

Matching a ranked node to a reference entity uses the same normalisation the entity
scorer uses (casefold, strip articles and punctuation) plus the node's `entity_labels`,
so "Mira" matches the reference's "Mira Quell". Reference entities the ranker never saw
are counted as misses, not skipped -- excluding them would flatter the recall metrics.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.repository import Repository  # noqa: E402
from storyweave.query import fence  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r6.db"
ANNOTATIONS = REPO_ROOT / "evidence" / "annotation"
CHAPTERS = (9, 17, 37)
SLUG = "the-ninth-house"

#: v1's ranking, by fenced payload degree. R0 and R1, both [MEASURED].
V1 = {"P@10 (R0)": 0.4000, "MAP (R0)": 0.4414, "P@10 (after R1)": 0.3000,
      "MAP (after R1)": 0.3668}


def norm(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    return re.sub(r"\s+", " ", s)


def precision_at_k(labels: list[int], k: int) -> float:
    top = labels[:k]
    return sum(top) / len(top) if top else 0.0


def average_precision(labels: list[int]) -> float:
    hits = 0
    total = 0.0
    for i, rel in enumerate(labels, start=1):
        if rel:
            hits += 1
            total += hits / i
    positives = sum(labels)
    return total / positives if positives else 0.0


def auc(labels: list[int]) -> float:
    """Rank-based AUC: P(a positive outranks a negative). Ties are impossible here."""
    pos = [i for i, x in enumerate(labels) if x]
    neg = [i for i, x in enumerate(labels) if not x]
    if not pos or not neg:
        return float("nan")
    wins = sum(1 for p in pos for n in neg if p < n)
    return wins / (len(pos) * len(neg))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--annotations", type=Path, default=ANNOTATIONS)
    ap.add_argument("--slug", default=SLUG)
    args = ap.parse_args(argv)

    repo = Repository(args.db)
    work = repo.get_work_by_slug(args.slug)
    assert work is not None and work.id is not None

    print("=" * 74)
    print("R6 SALIENCE vs the annotation's `significant` flag")
    print("=" * 74)
    print("\nFeatures (equal weight, fixed before scoring): lifetime_mentions,")
    print("recent_mentions, chapter_spread, has_proper_name, speaks_dialogue.")
    print("Edge degree is NOT a feature -- R1 measured why.\n")

    per_chapter: dict[int, dict[str, float]] = {}
    for chapter in CHAPTERS:
        data = json.loads((args.annotations / f"ch{chapter:02d}.json").read_text("utf-8"))
        significant = {
            norm(str(e["name"])) for e in data["entities"] if e.get("significant")
        }
        all_ref = {norm(str(e["name"])) for e in data["entities"]}

        ranked = fence.visible_cast_ranked(repo, work.id, chapter)
        labels: list[int] = []
        rows: list[tuple[str, int]] = []
        for node in ranked:
            names = {norm(node.name)}
            if node.id is not None:
                names |= {norm(x.label) for x in repo.list_entity_labels(node.id)}
            if not (names & all_ref):
                continue  # the reference has no opinion about this node
            hit = 1 if (names & significant) else 0
            labels.append(hit)
            rows.append((node.name, hit))

        metrics = {
            "AUC": auc(labels),
            "P@10": precision_at_k(labels, 10),
            "P@20": precision_at_k(labels, 20),
            "MAP": average_precision(labels),
        }
        per_chapter[chapter] = metrics
        print(f"--- chapter {chapter} --- {len(labels)} ranked nodes the reference knows, "
              f"{sum(labels)} of them significant")
        print("    " + "  ".join(f"{k}={v:.4f}" for k, v in metrics.items()))
        print("    top 10: " + ", ".join(
            f"{n}{'*' if h else ''}" for n, h in rows[:10]))
        print()

    print("--- pooled (mean over the three annotated chapters) ---")
    import math

    for k in ("AUC", "P@10", "P@20", "MAP"):
        vals = [per_chapter[c][k] for c in CHAPTERS if not math.isnan(per_chapter[c][k])]
        if not vals:
            print(f"    {k:<6} UNDEFINED everywhere")
            continue
        note = "" if len(vals) == len(CHAPTERS) else f"   (defined at {len(vals)}/3 chapters)"
        print(f"    {k:<6} {sum(vals) / len(vals):.4f}{note}")

    # The honest caveat, printed with the numbers rather than left to the report.
    degenerate = [
        c for c in CHAPTERS
        if math.isnan(per_chapter[c]["AUC"])
    ]
    if degenerate:
        print()
        print(f"    CAVEAT: at chapter(s) {degenerate} every matched reference entity is")
        print("    flagged `significant`, so there are no negatives. AUC is undefined")
        print("    there, and P@k cannot score below 1.0 however the nodes are ordered --")
        print("    those chapters inflate the pooled precision and cannot discriminate.")

    print("\n--- v1's degree-based ranking, for comparison ---")
    for k, v in V1.items():
        print(f"    {k:<18} {v:.4f}")
    print("\n(* marks a node the reference flags as significant)")
    repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
