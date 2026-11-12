"""Structural salience ranking: degree vs. mention count, at fixed chapters.

DELIVERABLE 2 of the v1 evaluation. There is no salience ranker in this codebase (see
``evidence/BASELINE.md``: a search for ``salience|disparity`` returns zero code hits), so
this measures the two structural signals the schema actually carries and asks whether
they agree:

* **degree** -- incident edges in the payload the API sends at chapter N, i.e. what the
  reader can actually see. Computed by reusing ``tools/graph_metrics.visible_api_payload``
  (which reuses ``query/fence.py``), so the DiGraph collapse described in BASELINE.md
  defect #1 is included, exactly as it is in the served graph.
* **mention count** -- the schema DOES have one: ``mentions`` rows carry ``node_id`` and
  ``chapter_ordinal``. Counted here over mentions whose ``chapter_ordinal <= N`` and
  whose node is fenced-visible at N, using the existing ``repository.list_mentions``
  read; no new SQL is introduced.

NO ground-truth metric is computed. P@k, MAP and AUC need a reference annotation and are
deliberately absent.

Usage:
    python tools/eval_salience.py --db storyweave-demo.sqlite \
        --slug the-ninth-house --chapters 10,20,30,40 --out evidence/salience_v1.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

# Make the repo root importable when run as `python tools/eval_salience.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import Mention  # noqa: E402
from storyweave.db.repository import Repository  # noqa: E402
from storyweave.query import fence  # noqa: E402
from tools import swconfig  # noqa: E402
from tools.graph_metrics import parse_chapters, payload_edges  # noqa: E402

FIELDNAMES: tuple[str, ...] = (
    "slug",
    "chapter",
    "node_id",
    "name",
    "type",
    "degree",
    "mention_count",
    "rank_degree",
    "rank_mentions",
)

TOP_K = 20

#: One measured entity row. `object` values are int/float/str; the float()/int() calls
#: below narrow them at the point of use.
Row = dict[str, Any]


def average_ranks(values: list[float]) -> list[float]:
    """Competition-free average ranks, 1 = largest. Ties share their mean rank.

    Written out rather than imported: scipy is not a dependency of either venv, and the
    tie handling has to be explicit anyway because ties are the thing being counted.
    """
    order = sorted(range(len(values)), key=lambda i: -values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> float:
    """Spearman's rho = Pearson correlation of the average ranks (tie-corrected)."""
    if len(a) < 2:
        raise ValueError("Spearman needs at least 2 observations")
    ra = np.asarray(average_ranks(a))
    rb = np.asarray(average_ranks(b))
    if ra.std() == 0 or rb.std() == 0:
        raise ValueError("Spearman undefined: one ranking is entirely tied")
    return float(np.corrcoef(ra, rb)[0, 1])


def measure_chapter(
    repo: Repository, work_id: int, chapter: int, mentions: list[Mention]
) -> list[Row]:
    """One row per fenced-visible entity at this chapter."""
    nodes = fence.visible_nodes(repo, work_id, chapter)
    visible_ids = {n.id for n in nodes}

    degree: Counter[int] = Counter({n.id or 0: 0 for n in nodes})
    for source, target, _relation, _span in payload_edges(repo, work_id, chapter):
        degree[source] += 1
        degree[target] += 1

    # Mention count, fenced two ways: the mention must be in a read chapter AND its
    # node must be revealed. Aggregated in Python over the existing list_mentions read.
    mention_count: Counter[int] = Counter({n.id or 0: 0 for n in nodes})
    for mention in mentions:
        if mention.node_id is None:
            continue  # an unclustered candidate belongs to no entity
        if mention.chapter_ordinal > chapter:
            continue
        if mention.node_id not in visible_ids:
            continue
        mention_count[mention.node_id] += 1

    degrees = [float(degree[n.id or 0]) for n in nodes]
    counts = [float(mention_count[n.id or 0]) for n in nodes]
    rank_d = average_ranks(degrees)
    rank_m = average_ranks(counts)

    return [
        {
            "node_id": node.id,
            "name": node.name,
            "type": node.type.value,
            "degree": int(degrees[i]),
            "mention_count": int(counts[i]),
            "rank_degree": rank_d[i],
            "rank_mentions": rank_m[i],
        }
        for i, node in enumerate(nodes)
    ]


def top_table(rows: list[Row], key: str, rank_key: str) -> str:
    top = sorted(rows, key=lambda r: (-float(r[key]), str(r["name"])))[:TOP_K]
    width = max(len(str(r["name"])) for r in top)
    lines = [f"{'#':>3}  {'name'.ljust(width)}  {'type':<12} {key:>14}  rank"]
    for i, row in enumerate(top, 1):
        lines.append(
            f"{i:>3}  {str(row['name']).ljust(width)}  {str(row['type']):<12} "
            f"{row[key]:>14}  {row[rank_key]:.1f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="storyweave-demo.sqlite", type=Path)
    ap.add_argument("--slug", default="the-ninth-house")
    ap.add_argument("--chapters", default="10,20,30,40")
    ap.add_argument("--out", default=Path("evidence/salience_v1.csv"), type=Path)
    args = ap.parse_args(argv)

    chapters = parse_chapters(args.chapters)
    repo = swconfig.open_readonly(args.db)
    try:
        work = repo.get_work_by_slug(args.slug)
        if work is None or work.id is None:
            raise ValueError(f"work {args.slug!r} not found in {args.db}")
        mentions = repo.list_mentions(work.id)
        print(f"=== salience (structural) — {args.slug} ===")
        print(f"database: {Path(args.db).resolve()} (mode=ro)")
        print(f"mentions rows for this work: {len(mentions)}")
        unclustered = sum(1 for m in mentions if m.node_id is None)
        print(f"  of which unclustered (node_id IS NULL, excluded): {unclustered}")

        csv_rows: list[Row] = []
        for chapter in chapters:
            rows = measure_chapter(repo, work.id, chapter, mentions)
            csv_rows += [{"slug": args.slug, "chapter": chapter, **r} for r in rows]

            print(f"\n--- chapter {chapter}: {len(rows)} fenced-visible entities ---")
            print(f"\nTop {TOP_K} by DEGREE")
            print(top_table(rows, "degree", "rank_degree"))
            print(f"\nTop {TOP_K} by MENTION COUNT")
            print(top_table(rows, "mention_count", "rank_mentions"))

            rho = spearman(
                [float(r["degree"]) for r in rows],
                [float(r["mention_count"]) for r in rows],
            )
            # "Ties on degree within the top 20": among the 20 highest-degree entities,
            # how many share their degree value with another entity in that same top 20.
            top20 = sorted(rows, key=lambda r: (-float(r["degree"]), str(r["name"])))[:TOP_K]
            counts = Counter(int(r["degree"]) for r in top20)
            tied = sum(c for c in counts.values() if c > 1)
            groups = sum(1 for c in counts.values() if c > 1)
            print(
                f"\nSpearman rho (degree vs mention_count, all {len(rows)} entities): "
                f"{rho:.4f}"
            )
            print(
                f"Entities tied on degree within the top {TOP_K}: {tied} "
                f"(in {groups} tied group(s); {len(counts)} distinct degree values)"
            )

        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(FIELDNAMES))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\nwrote {args.out} ({len(csv_rows)} rows)")
        return 0
    finally:
        repo.close()


if __name__ == "__main__":
    raise SystemExit(main())
