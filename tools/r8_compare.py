"""R8: the like-for-like v1-vs-final comparison, measured through the real API.

    .\\dev.ps1
    python tools/r8_compare.py

Two numbers that only make sense side by side:

* **what the client is handed** at chapters 10/20/40 — v1 served one payload per chapter
  with no display controls at all, so its figure is simply "the fenced graph". The final
  system's comparable figure is its DEFAULT view (Characters, cast 20), because that is
  what a reader actually gets; `cast=all` is reported beside it so the comparison cannot
  be accused of flattering the default by hiding the rest.
* **how long a graph request takes**, median of repeated calls through FastAPI's
  TestClient. Same process, same machine, same chapter set, so the two are comparable to
  each other even though neither is a production latency figure.

Both DBs are opened read-only by the API; nothing here writes.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # the real import stays inside _client, to keep the CLI import light
    from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_DB = REPO_ROOT / "evidence" / "v1_ninth_house.db"
FINAL_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r6.db"
SLUG = "the-ninth-house"
CHAPTERS = (10, 20, 40)
REPEATS = 15


def _client(db: Path) -> TestClient:
    from fastapi.testclient import TestClient

    from storyweave.api.app import create_app
    from storyweave.config import get_settings

    get_settings.cache_clear()
    os.environ["STORYWEAVE_DB_PATH"] = str(db)
    return TestClient(create_app())


def _graph(client: TestClient, base: str, n: int, **params: str) -> tuple[int, int]:
    r = client.get(f"{base}/graph", params={"n": n, **params})
    r.raise_for_status()
    el = r.json()["elements"]
    return len(el["nodes"]), len(el["edges"])


def _median_ms(client: TestClient, base: str, n: int, **params: str) -> float:
    timings: list[float] = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        client.get(f"{base}/graph", params={"n": n, **params}).raise_for_status()
        timings.append((time.perf_counter() - start) * 1000)
    return statistics.median(timings)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v1", type=Path, default=V1_DB)
    ap.add_argument("--final", type=Path, default=FINAL_DB)
    args = ap.parse_args(argv)

    base = f"/api/v1/works/{SLUG}"
    print("=" * 74)
    print("R8 LIKE-FOR-LIKE: what the client is handed, and how long it waits")
    print("=" * 74)

    print(f"\nv1  = {args.v1}")
    print(f"final = {args.final}\n")

    # The frozen v1 DB is read-only and `initialize_schema` would try to migrate it
    # (CLAUDE.md: never modify the frozen artifacts). Serve a scratch COPY instead, inside
    # .local	mp on F:, and say so rather than silently reading something else.
    import shutil
    import tempfile

    scratch = Path(tempfile.mkdtemp(dir=REPO_ROOT / ".local" / "tmp", prefix="r8_v1_"))
    v1_copy = scratch / args.v1.name
    shutil.copy2(args.v1, v1_copy)
    # copy2 preserves the read-only attribute, which is exactly what makes the original
    # safe and the copy useless — the API migrates the schema on open. Clear it here, on
    # the scratch copy only.
    v1_copy.chmod(0o644)
    print(f"   (scratch copy of the frozen DB at {v1_copy}; the original is untouched)")
    print()
    v1 = _client(v1_copy)
    print("--- v1: the whole fenced graph (it had no display controls) ---")
    v1_sizes: dict[int, tuple[int, int]] = {}
    for n in CHAPTERS:
        v1_sizes[n] = _graph(v1, base, n, cast="all", types="Character,Organization,Place,Item")
        print(f"   ch{n:<3} dots={v1_sizes[n][0]:>4}  lines={v1_sizes[n][1]:>5}")
    v1_ms = {n: _median_ms(v1, base, n, cast="all", types="Character,Organization,Place,Item")
             for n in CHAPTERS}

    final = _client(args.final)
    print("\n--- final: the DEFAULT view (Characters, cast 20) ---")
    for n in CHAPTERS:
        dots, lines = _graph(final, base, n)
        was = f"{v1_sizes[n][0]}/{v1_sizes[n][1]}"
        print(f"   ch{n:<3} dots={dots:>4}  lines={lines:>5}   (v1 was {was})")
    print("\n--- final: 'Everyone', every type — the widest it goes ---")
    for n in CHAPTERS:
        dots, lines = _graph(final, base, n, cast="all", types="Character,Organization,Place,Item")
        print(f"   ch{n:<3} dots={dots:>4}  lines={lines:>5}")

    final_ms = {n: _median_ms(final, base, n) for n in CHAPTERS}
    final_all_ms = {n: _median_ms(final, base, n, cast="all",
                                  types="Character,Organization,Place,Item")
                    for n in CHAPTERS}

    print(f"\n--- median graph request, {REPEATS} calls each (same process) ---")
    print(f"   {'chapter':>8} {'v1 (all)':>12} {'final default':>15} {'final all':>12}")
    for n in CHAPTERS:
        print(f"   {n:>8} {v1_ms[n]:>11.1f}ms {final_ms[n]:>14.1f}ms {final_all_ms[n]:>11.1f}ms")

    print("\nNOTE: TestClient timings, one process, no network. Comparable to each other,")
    print("not a production latency figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
