"""Build the retrofit R6 database: R5's graph plus per-chapter salience ranks.

    .\\dev.ps1
    python tools/build_r6_db.py

Copies `ninth_house_r5.db` to `ninth_house_r6.db` and computes `node_salience` for every
chapter. No model runs; this is arithmetic over stored mentions. The frozen baseline is
never opened.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.repository import Repository  # noqa: E402
from storyweave.graph.salience import FEATURES, compute_salience  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data" / "retrofit" / "ninth_house_r5.db"
DEFAULT_OUT = REPO_ROOT / "data" / "retrofit" / "ninth_house_r6.db"
SLUG = "the-ninth-house"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--slug", default=SLUG)
    args = ap.parse_args(argv)

    if not args.source_db.exists():
        print(f"ERROR: {args.source_db} missing")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        args.out.unlink()
    shutil.copy(args.source_db, args.out)
    args.out.chmod(0o644)

    print(f"source : {args.source_db}")
    print(f"output : {args.out}")
    print(f"features (equal weight): {', '.join(FEATURES)}")
    print("edge degree is deliberately NOT a feature (R1 measured why)")

    with Repository(args.out) as repo:
        repo.initialize_schema()  # idempotent; adds node_salience to the copy
        work = repo.get_work_by_slug(args.slug)
        assert work is not None and work.id is not None
        report = compute_salience(work.id, repo)
        print(f"\n{report.summary()}")
        print("\neligible cast per chapter (the significance gate):")
        for ch in sorted(report.eligible_per_chapter):
            if ch in (1, 5, 10, 20, 30, 40):
                print(f"  ch{ch:>3}: {report.eligible_per_chapter[ch]}")
        print("\ntop 10 at chapter 40:")
        for node in repo.list_salience_ranked(work.id, 40, 10):
            print(f"  {node.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
