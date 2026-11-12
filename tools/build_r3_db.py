"""Re-extract a work under the retrofit R3 rules into a fresh database.

    .\\dev.ps1 -Ml
    python tools/check_local_env.py
    python tools/build_r3_db.py

Ingests the corpus, then runs the GLiNER floor with R3's four-type prompt set, the
five-rule abbreviation merge and title linking, writing `data/retrofit/ninth_house_r3.db`.
Never touches the frozen baseline: the output path is separate and the input is read-only
sample text.

Tier-1 co-occurrence stays off (retrofit R1, `relations.cooccurrence_enabled = false`), so
this database has entities, labels and no rule edges — which is the intended R3 state. R4
supplies the edges.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.repository import Repository  # noqa: E402
from storyweave.ingest.pipeline import ingest as run_ingest  # noqa: E402
from storyweave.ingest.work_config import (  # noqa: E402
    find_work_config,
    load_work_config,
)
from storyweave.nlp.cluster import cluster_mentions_detailed  # noqa: E402
from storyweave.nlp.pipeline import extract_work  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data" / "samples" / "the-ninth-house"
DEFAULT_OUT = REPO_ROOT / "data" / "retrofit" / "ninth_house_r3.db"


def build(source: Path, out: Path) -> int:
    if out.exists():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)

    config = load_work_config(find_work_config(source))
    print(f"source : {source}")
    print(f"output : {out}")
    print(
        f"config : abbreviation window={config.clustering.abbreviation_chapter_window}, "
        f"merge_abbreviations={config.clustering.merge_abbreviations}, "
        f"cooccurrence_enabled={config.relations.cooccurrence_enabled}"
    )

    with Repository(out) as repo:
        repo.initialize_schema()
        ingest_report = run_ingest(source, repo, config)
        print(f"ingest : {ingest_report.summary()}")

        work = repo.get_work_by_slug(ingest_report.work_slug)
        assert work is not None and work.id is not None
        extract_report = extract_work(work.id, repo, config)
        print(f"extract: {extract_report.summary()}")

        print("\nentities by type:")
        for node_type, n in sorted(
            extract_report.per_type.items(), key=lambda kv: (-kv[1], kv[0].value)
        ):
            print(f"  {node_type.value:<14} {n:>4}")

        labels = repo.conn.execute(
            "SELECT kind, COUNT(*) FROM entity_labels GROUP BY kind ORDER BY 2 DESC"
        ).fetchall()
        print("\nentity_labels by kind:")
        for kind, n in labels:
            print(f"  {str(kind):<14} {n:>4}")

        # Re-derive the merge decisions so the under-merge list can be reported in full.
        outcome = cluster_mentions_detailed(repo.list_mentions(work.id), config.clustering)
        print(f"\nalias merges made   : {len(outcome.merges)}")
        print(f"alias merges refused: {len(outcome.under_merges)}")
        reasons = Counter(d.reason.split(":")[0] for d in outcome.under_merges)
        for reason, n in reasons.most_common():
            print(f"  {reason:<28} {n:>4}")
        print("\nevery refusal, in full:")
        for d in sorted(outcome.under_merges, key=lambda d: d.short):
            print(f"  {d.short!r} -/-> {d.host!r}: {d.reason}")

        print(f"\ntitle links accepted: {extract_report.title_links}")
        print(f"title links refused : {extract_report.titles_rejected}")
        for row in repo.conn.execute(
            """SELECT l.label, l.revealed_chapter, n.name, l.quote
                 FROM entity_labels l JOIN nodes n ON n.id = l.entity_id
                WHERE l.kind = 'title' ORDER BY l.revealed_chapter, l.label"""
        ):
            print(f"  ch{row[1]:>2} {row[0]!r} -> {row[2]!r}  quote: {row[3]!r}")

        stored = Counter(n.type.value for n in repo.list_nodes(work.id))
        print(f"\nstored node types: {dict(stored)}")
        assert set(stored) <= {"Character", "Organization", "Place", "Item"}, stored
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=DEFAULT_SOURCE, type=Path)
    ap.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = ap.parse_args(argv)
    return build(args.source, args.out)


if __name__ == "__main__":
    sys.exit(main())
