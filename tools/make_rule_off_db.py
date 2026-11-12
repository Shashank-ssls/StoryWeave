"""Derive the rule-off database for retrofit R1: v1 minus every co-occurrence edge.

R1 measures what the graph is worth once Tier-1 co-occurrence is switched off. Rather
than re-extract (which would change entities too, and make the comparison not
like-for-like), this copies the frozen v1 database and deletes only the edges whose
provenance is ``rule``. Entities, mentions, chapters, curated Tier-2/Tier-3 edges and
every reveal stamp are byte-for-byte what v1 had, so any score difference is
attributable to the co-occurrence edges and nothing else.

    python tools/make_rule_off_db.py            # writes evidence/retrofit/r1_rule_off.db

The source is opened read-only and never written. The output is regenerable, so it is
gitignored; the script is the artifact.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import stat
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = REPO_ROOT / "evidence" / "v1_ninth_house.db"
DEFAULT_OUT = REPO_ROOT / "evidence" / "retrofit" / "r1_rule_off.db"
DROPPED_METHOD = "rule"
DEFAULT_SLUG = "the-ninth-house"


def work_id(conn: sqlite3.Connection, slug: str) -> int:
    row = conn.execute("SELECT id FROM works WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise SystemExit(f"work not in database: {slug}")
    return int(row[0])


def counts(conn: sqlite3.Connection, wid: int) -> Counter[str]:
    """Edge count per extraction_method for one work."""
    return Counter(
        {
            str(method): int(n)
            for method, n in conn.execute(
                "SELECT extraction_method, COUNT(*) FROM edges WHERE work_id = ? "
                "GROUP BY extraction_method",
                (wid,),
            )
        }
    )


def build(src: Path, out: Path, slug: str = DEFAULT_SLUG) -> int:
    """Copy `src` to `out` and delete `slug`'s `rule` edges. Returns rows deleted.

    Scoped to one work on purpose: the other work in the baseline is the seeded
    Hollow Crown, which is the fence's own regression fixture and stays untouched.
    """
    if not src.is_file():
        raise SystemExit(f"source database not found: {src}")

    with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as ro:
        wid = work_id(ro, slug)
        before = counts(ro, wid)
        other_before = dict(
            ro.execute(
                "SELECT extraction_method, COUNT(*) FROM edges WHERE work_id != ? "
                "GROUP BY extraction_method",
                (wid,),
            )
        )
    print(f"source {src}")
    print(f"  work: {slug} (work_id={wid})")
    print(f"  edges by method: {dict(sorted(before.items()))} (total {sum(before.values())})")

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.chmod(stat.S_IWRITE | stat.S_IREAD)
        out.unlink()
    shutil.copy2(src, out)
    # copy2 preserves mode bits and the frozen baseline is deliberately read-only.
    out.chmod(stat.S_IWRITE | stat.S_IREAD)

    conn = sqlite3.connect(out)
    try:
        deleted = conn.execute(
            "DELETE FROM edges WHERE work_id = ? AND extraction_method = ?",
            (wid, DROPPED_METHOD),
        ).rowcount
        conn.commit()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        after = counts(conn, wid)
        other_after = dict(
            conn.execute(
                "SELECT extraction_method, COUNT(*) FROM edges WHERE work_id != ? "
                "GROUP BY extraction_method",
                (wid,),
            )
        )
    finally:
        conn.close()

    print(f"output {out}")
    print(f"  deleted {deleted} edges with extraction_method='{DROPPED_METHOD}'")
    print(f"  edges by method: {dict(sorted(after.items()))} (total {sum(after.values())})")
    print(f"  other works' edges: {dict(sorted(other_after.items()))} (unchanged)")
    print(f"  PRAGMA integrity_check: {integrity}")

    if after.get(DROPPED_METHOD):
        raise SystemExit(f"rule edges survived the delete: {after[DROPPED_METHOD]}")
    if before.get(DROPPED_METHOD, 0) != deleted:
        raise SystemExit(f"expected to delete {before.get(DROPPED_METHOD, 0)}, deleted {deleted}")
    for method, n in before.items():
        if method != DROPPED_METHOD and after.get(method, 0) != n:
            raise SystemExit(f"non-rule edges changed: {method} {n} -> {after.get(method, 0)}")
    if other_before != other_after:
        raise SystemExit(f"other works changed: {other_before} -> {other_after}")
    if integrity != "ok":
        raise SystemExit(f"integrity_check failed: {integrity}")
    return deleted


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=DEFAULT_SRC, type=Path, help="frozen v1 database")
    ap.add_argument("--out", default=DEFAULT_OUT, type=Path, help="derived rule-off database")
    ap.add_argument("--slug", default=DEFAULT_SLUG, help="work whose rule edges are dropped")
    args = ap.parse_args(argv)
    build(args.src, args.out, args.slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
