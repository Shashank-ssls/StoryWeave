"""R4 recall accounting: for every gold relation, WHICH STAGE lost it.

    .\\dev.ps1
    python tools/r4_recall_audit.py

The R4 brief calls this the most important output of the phase, and it is: a micro-F1
of zero says the pipeline missed everything, but says nothing about where to spend the
next day of work. This attributes each of the annotation's gold relations to exactly one
stage:

  NOT_IN_THE_TWELVE  the relation is outside the closed list by design (retrofit rule 3)
  ENTITY_MISSING     R3 never created one (or both) of the endpoints
  NO_PROPOSAL        both endpoints exist, but relex never proposed this pair
  WRONG_TYPE         relex proposed this pair, with a different relation
  VALIDATOR_REJECTED relex proposed it correctly and the validator refused it (+reason)
  GRADE_INFERRED     it survived validation but is not STATED, so it is not served
  FOUND              it is in the shipped STATED graph

Stages are tested in that order, so each gold relation lands in exactly one bucket and
the counts sum to the size of the key.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import LEGACY_RELATION_MAP  # noqa: E402
from storyweave.db.repository import Repository  # noqa: E402
from tools import swconfig  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r4.db"
DEFAULT_PROPOSALS = REPO_ROOT / "evidence" / "retrofit" / "R4_proposals.jsonl"
ANNOTATION_DIR = REPO_ROOT / "evidence" / "annotation"
CHAPTERS = (9, 17, 37)
SLUG = "the-ninth-house"

STAGES = (
    "FOUND",
    "GRADE_INFERRED",
    "VALIDATOR_REJECTED",
    "WRONG_TYPE",
    "NO_PROPOSAL",
    "ENTITY_MISSING",
    "NOT_IN_THE_TWELVE",
)


def normalize(surface: str) -> str:
    """The same shape of normalisation the clusterer uses: casefold, strip articles."""
    s = re.sub(r"[^\w\s-]", "", surface.lower()).strip()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    return re.sub(r"\s+", " ", s)


def build_name_index(repo: Repository, work_id: int) -> dict[str, int]:
    """Every name the database knows for an entity -> its node id."""
    index: dict[str, int] = {}
    for node in repo.list_nodes(work_id):
        if node.id is None:
            continue
        index.setdefault(normalize(node.name), node.id)
        for label in repo.list_entity_labels(node.id):
            index.setdefault(normalize(label.label), node.id)
    return index


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--proposals", type=Path, default=DEFAULT_PROPOSALS)
    ap.add_argument("--annotations", type=Path, default=ANNOTATION_DIR)
    ap.add_argument("--slug", default=SLUG)
    args = ap.parse_args(argv)

    repo = swconfig.open_readonly(args.db)
    try:
        work = repo.get_work_by_slug(args.slug)
        assert work is not None and work.id is not None
        names = build_name_index(repo, work.id)
        edges = repo.list_edges(work.id)
    finally:
        repo.close()

    # What the shipped graph has, and at what grade.
    shipped: dict[tuple[int, int, str], str] = {}
    for e in edges:
        if e.extraction_method.value == "curated":
            continue  # not extraction output; scored separately
        grade = e.grade.value if e.grade is not None else "NONE"
        shipped[(e.source_id, e.target_id, e.relation)] = grade

    # Every proposal relex made, keyed by unordered pair.
    proposals_by_pair: dict[frozenset[int], list[dict[str, Any]]] = defaultdict(list)
    with args.proposals.open(encoding="utf-8") as fh:
        for line in fh:
            p = json.loads(line)
            if p["source_id"] is None or p["target_id"] is None:
                continue
            proposals_by_pair[frozenset({p["source_id"], p["target_id"]})].append(p)

    rows: list[tuple[str, str, str]] = []  # (stage, detail, label)
    for chapter in CHAPTERS:
        data = json.loads((args.annotations / f"ch{chapter:02d}.json").read_text("utf-8"))
        for relation in data.get("relations", []):
            old = str(relation["relation"])
            label = f"ch{chapter:02d} {relation['source']} -{old}-> {relation['target']}"
            entry = LEGACY_RELATION_MAP.get(old)
            if entry is None or entry[1] is None:
                fate = entry[0].value if entry else "UNKNOWN"
                rows.append(("NOT_IN_THE_TWELVE", fate, label))
                continue
            _fate, new, reverse = entry
            assert new is not None  # narrowed by the branch above
            src_name, tgt_name = str(relation["source"]), str(relation["target"])
            if reverse:
                src_name, tgt_name = tgt_name, src_name
            src = names.get(normalize(src_name))
            tgt = names.get(normalize(tgt_name))
            if src is None or tgt is None:
                missing = [n for n, i in ((src_name, src), (tgt_name, tgt)) if i is None]
                rows.append(("ENTITY_MISSING", ", ".join(missing), label))
                continue
            shipped_grade = shipped.get((src, tgt, new.value)) or shipped.get(
                (tgt, src, new.value)
            )
            if shipped_grade == "STATED":
                rows.append(("FOUND", new.value, label))
                continue
            if shipped_grade is not None:
                rows.append(("GRADE_INFERRED", new.value, label))
                continue
            pair = proposals_by_pair.get(frozenset({src, tgt}), [])
            right_type = [p for p in pair if p["relation"] == new.value]
            if right_type:
                reasons = sorted({p["reason"] or "ACCEPTED_ELSEWHERE" for p in right_type})
                rows.append(("VALIDATOR_REJECTED", ", ".join(reasons), label))
            elif pair:
                proposed = sorted({p["relation"] for p in pair})
                rows.append(("WRONG_TYPE", f"proposed {', '.join(proposed)}", label))
            else:
                rows.append(("NO_PROPOSAL", "relex proposed nothing for this pair", label))

    counts = Counter(stage for stage, _d, _l in rows)
    print("=" * 78)
    print("R4 RECALL ACCOUNTING - where each gold relation was lost")
    print("=" * 78)
    print(f"\ngold relations in the key: {len(rows)}\n")
    print(f"{'stage':<20} {'n':>4}   {'share':>7}")
    print("-" * 78)
    for stage in STAGES:
        n = counts.get(stage, 0)
        print(f"{stage:<20} {n:>4}   {n / len(rows):>6.1%}")
    print("-" * 78)
    print(f"{'TOTAL':<20} {sum(counts.values()):>4}")

    print("\n\nEvery gold relation, by stage:\n")
    for stage in STAGES:
        group = [(d, lab) for s, d, lab in rows if s == stage]
        if not group:
            continue
        print(f"--- {stage} ({len(group)}) ---")
        for detail, label in sorted(group, key=lambda g: g[1]):
            print(f"  {label}")
            print(f"      {detail}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
