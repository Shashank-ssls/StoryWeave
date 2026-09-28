"""Migration: add `entity_labels` to an existing database and backfill it (retrofit R3).

Up: create the table (via the normal schema, which is `CREATE TABLE IF NOT EXISTS`), then
populate one label per entity from the data the database already has —

  * the node's canonical name, as the `full`, primary label, revealed at the node's own
    `revealed_chapter`;
  * every other distinct mention surface for that node, as a `short` label, revealed at
    the chapter that surface first appears in.

The reveal chapter of an alias is the chapter the READER first sees that spelling, which
is the whole reason the table exists: "Drask" may not be readable until several chapters
after "Warden-Captain Orin Drask". Backfilling it from `nodes.revealed_chapter` alone
would leak every alias to the entity's first chapter.

No node rows are touched and no type is rewritten — legacy Ability/Concept/Event/Title
rows stay exactly as they are (rule I2, and the R3 decision that nothing migrates).

Down: drop the table. `entity_labels` is derived data, so dropping it loses nothing that
`up` cannot rebuild; a node's canonical name lives in `nodes.name` regardless.

    python tools/migrate_entity_labels.py --db path/to.db          # up
    python tools/migrate_entity_labels.py --db path/to.db --down   # down

Refuses to run against a read-only database, so it can never touch the frozen baseline.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.models import EntityLabel, LabelKind  # noqa: E402
from storyweave.db.repository import Repository  # noqa: E402


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def up(db: Path) -> int:
    """Create + backfill `entity_labels`. Returns the number of labels written."""
    written = 0
    with Repository(db) as repo:
        repo.initialize_schema()  # CREATE TABLE IF NOT EXISTS: adds only what is missing
        conn = repo.conn
        nodes = conn.execute(
            "SELECT id, work_id, name, revealed_chapter FROM nodes ORDER BY id"
        ).fetchall()
        for node in nodes:
            node_id = int(node["id"])
            canonical = str(node["name"])
            repo.add_entity_label(
                EntityLabel(
                    entity_id=node_id,
                    label=canonical,
                    kind=LabelKind.FULL,
                    revealed_chapter=int(node["revealed_chapter"]),
                    is_primary=True,
                    quote=None,
                )
            )
            written += 1
            # Distinct alias surfaces, each stamped with its own first appearance.
            rows = conn.execute(
                """SELECT surface, MIN(chapter_ordinal) AS first_chapter
                     FROM mentions
                    WHERE node_id = ?
                 GROUP BY surface
                 ORDER BY first_chapter, surface""",
                (node_id,),
            ).fetchall()
            for row in rows:
                surface = str(row["surface"]).strip()
                if not surface or surface == canonical:
                    continue
                repo.add_entity_label(
                    EntityLabel(
                        entity_id=node_id,
                        label=surface,
                        kind=LabelKind.SHORT,
                        revealed_chapter=int(row["first_chapter"]),
                        is_primary=False,
                        quote=None,
                    )
                )
                written += 1
    return written


def down(db: Path) -> None:
    """Drop `entity_labels`. Derived data; `up` rebuilds it."""
    conn = sqlite3.connect(db)
    try:
        conn.execute("DROP TABLE IF EXISTS entity_labels")
        conn.commit()
    finally:
        conn.close()


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path, help="database to migrate")
    ap.add_argument("--down", action="store_true", help="drop the table instead")
    args = ap.parse_args(argv)

    if not args.db.is_file():
        raise SystemExit(f"database not found: {args.db}")

    if args.down:
        down(args.db)
        print(f"down: dropped entity_labels from {args.db}")
        return 0

    written = up(args.db)
    with sqlite3.connect(f"file:{args.db}?mode=ro", uri=True) as ro:
        total = ro.execute("SELECT COUNT(*) FROM entity_labels").fetchone()[0]
        entities = ro.execute(
            "SELECT COUNT(DISTINCT entity_id) FROM entity_labels"
        ).fetchone()[0]
    print(f"up: wrote {written} labels to {args.db}")
    print(f"    entity_labels now holds {total} rows across {entities} entities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
