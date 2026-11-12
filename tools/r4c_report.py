"""R4c reporting: ring-1 / ring-2 edge counts and the default-view edge count.

    .\\dev.ps1
    python tools/r4c_report.py --db data/retrofit/ninth_house_r4c.db

Everything is read through ``query/fence.py`` and the row-based payload builder, so the
numbers are what the app would actually serve, not what the tables happen to contain.

**The "default view" is a MEASUREMENT PROJECTION defined here, not a shipped feature.**
The API has no cast-size parameter yet -- salience and the 4-clause query are R6's work.
So that the R4c verdict ("are there enough edges to show a reader?") can be answered now,
this tool defines the default view exactly as retrofit rules 2 and 7 describe it:

  * Characters only (rule 2: the default graph draws Characters);
  * the top N by IMPORTANCE COMPUTED FROM CHAPTERS <= n ONLY -- mentions up to the fenced
    chapter, never a book-wide rank, because a book-wide rank is a spoiler side channel
    (rule 7);
  * STATED edges only, because that is the only grade the graph serves (rule 4);
  * both endpoints inside the cast.

Ties are broken by first appearance then node id, so the cast is deterministic.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import RING1_RELATIONS, RING2_RELATIONS, NodeType  # noqa: E402
from storyweave.db.repository import Repository  # noqa: E402
from storyweave.query import fence  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r4c.db"
CHAPTERS = (10, 20, 30, 40)
SLUG = "the-ninth-house"

RING1 = {r.value for r in RING1_RELATIONS}
RING2 = {r.value for r in RING2_RELATIONS}


def cast_at(repo: Repository, work_id: int, chapter: int, size: int) -> list[int]:
    """The top ``size`` Character node ids at ``chapter``, ranked with no future info."""
    visible = [
        n for n in fence.visible_graph_nodes(repo, work_id, chapter)
        if n.type is NodeType.CHARACTER and n.id is not None
    ]
    # Mentions up to and including `chapter` only. Rule 7: a book-wide rank leaks.
    counts: Counter[int] = Counter()
    for m in repo.list_mentions(work_id):
        if m.node_id is not None and m.chapter_ordinal <= chapter:
            counts[m.node_id] += 1
    ranked = sorted(
        visible,
        key=lambda n: (-counts.get(n.id or 0, 0), n.first_seen_chapter, n.id or 0),
    )
    return [n.id for n in ranked[:size] if n.id is not None]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--slug", default=SLUG)
    ap.add_argument("--cast", type=int, default=20)
    args = ap.parse_args(argv)

    repo = Repository(args.db)
    work = repo.get_work_by_slug(args.slug)
    assert work is not None and work.id is not None

    print("=" * 78)
    print(f"R4c REPORT -- {args.db.name}")
    print("=" * 78)

    print("\n1. FENCED EDGES BY RING (all types drawn, all grades)\n")
    print(f"{'chapter':>8} {'nodes':>7} {'edges':>7} {'ring1':>7} {'ring2':>7} "
          f"{'STATED':>7} {'INFERRED':>9}")
    print("-" * 60)
    for ch in CHAPTERS:
        nodes = fence.visible_graph_nodes(repo, work.id, ch)
        drawn = {n.id for n in nodes}
        edges = [
            e for e in fence.visible_edges(repo, work.id, ch)
            if e.source_id in drawn and e.target_id in drawn
        ]
        r1 = sum(1 for e in edges if e.relation in RING1)
        r2 = sum(1 for e in edges if e.relation in RING2)
        st = sum(1 for e in edges if e.grade is not None and e.grade.value == "STATED")
        inf = sum(1 for e in edges if e.grade is not None and e.grade.value == "INFERRED")
        print(f"{ch:>8} {len(nodes):>7} {len(edges):>7} {r1:>7} {r2:>7} {st:>7} {inf:>9}")

    print("\n2. PER-RELATION, fenced at chapter 40\n")
    nodes40 = fence.visible_graph_nodes(repo, work.id, 40)
    drawn40 = {n.id for n in nodes40}
    edges40 = [
        e for e in fence.visible_edges(repo, work.id, 40)
        if e.source_id in drawn40 and e.target_id in drawn40
    ]
    per = Counter(e.relation for e in edges40)
    per_stated = Counter(
        e.relation for e in edges40 if e.grade is not None and e.grade.value == "STATED"
    )
    for rel in sorted(set(RING1) | set(RING2)):
        ring = "1" if rel in RING1 else "2"
        print(f"  ring{ring}  {rel:<14} total={per.get(rel, 0):>3}  "
              f"STATED={per_stated.get(rel, 0):>3}")

    print(f"\n3. DEFAULT VIEW at ch40 -- Characters only, cast={args.cast}, STATED only")
    print("   (a measurement projection defined in this tool's docstring, not an API)\n")
    cast = cast_at(repo, work.id, 40, args.cast)
    cast_set = set(cast)
    names = {n.id: n.name for n in nodes40}
    default_edges = [
        e for e in edges40
        if e.source_id in cast_set and e.target_id in cast_set
        and e.grade is not None and e.grade.value == "STATED"
    ]
    any_grade = [
        e for e in edges40 if e.source_id in cast_set and e.target_id in cast_set
    ]
    total_chars = sum(1 for n in nodes40 if n.type is NodeType.CHARACTER)
    print(f"   Characters visible at ch40 : {total_chars}")
    print(f"   cast shown                 : {len(cast)}")
    print(f"   DEFAULT-VIEW EDGES (STATED): {len(default_edges)}")
    print(f"   ... if INFERRED were shown : {len(any_grade)}")
    if default_edges:
        print()
        for e in default_edges:
            print(f"     {names.get(e.source_id)} -{e.relation}-> {names.get(e.target_id)}")
    print()
    print("   cast, in rank order:")
    for i, nid in enumerate(cast, 1):
        deg = sum(1 for e in default_edges if nid in (e.source_id, e.target_id))
        print(f"     {i:>2}. {names.get(nid, nid):<28} default-view degree {deg}")

    isolated = sum(
        1 for nid in cast
        if not any(nid in (e.source_id, e.target_id) for e in default_edges)
    )
    print(f"\n   isolated in the default view: {isolated} of {len(cast)}")
    repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
