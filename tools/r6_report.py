"""R6 measurement: the cast dial, payload density, the ego endpoint and D3.

    .\\dev.ps1
    python tools/r6_report.py --db data/retrofit/ninth_house_r6.db

Everything goes through the real API (FastAPI TestClient), not through the repository,
so what is measured is what a client actually receives.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from storyweave.api.app import API_PREFIX, create_app  # noqa: E402
from storyweave.config import get_settings  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r6.db"
SLUG = "the-ninth-house"
CHAPTERS = (10, 20, 30, 40)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--slug", default=SLUG)
    args = ap.parse_args(argv)

    get_settings.cache_clear()
    import os

    os.environ["STORYWEAVE_DB_PATH"] = str(args.db)
    client = TestClient(create_app())
    base = f"{API_PREFIX}/works/{args.slug}"

    def graph(n: int, cast: str = "20", types: str = "Character") -> tuple[int, int]:
        r = client.get(f"{base}/graph", params={"n": n, "cast": cast, "types": types})
        r.raise_for_status()
        el = r.json()["elements"]
        return len(el["nodes"]), len(el["edges"])

    print("=" * 74)
    print(f"R6 REPORT -- {args.db.name}  (through the API)")
    print("=" * 74)

    print("\n1. THE CAST DIAL -- v1's was a client-side no-op (defect D3)\n")
    print(f"   {'chapter':>8} {'cast=20':>16} {'cast=50':>16} {'cast=all':>16}")
    print("   " + "-" * 60)
    distinct = True
    for n in CHAPTERS:
        a, b, c = graph(n, "20"), graph(n, "50"), graph(n, "all")
        print(f"   {n:>8} {str(a):>16} {str(b):>16} {str(c):>16}")
        if n == 40 and not (a != b and b != c):
            distinct = False
    print(f"\n   ch40 payloads differ across 20 / 50 / all: {distinct}")

    print("\n2. DEFAULT VIEW (Characters only, cast 20) -- dots and lines\n")
    print(f"   {'chapter':>8} {'dots':>6} {'lines':>6}")
    print("   " + "-" * 24)
    for n in CHAPTERS:
        d, e = graph(n, "20", "Character")
        print(f"   {n:>8} {d:>6} {e:>6}")

    print("\n3. OVERLAYS at ch40 (each is opt-in; the default is Characters only)\n")
    for types in ("Character", "Character,Organization", "Character,Place",
                  "Character,Organization,Place,Item"):
        d, e = graph(40, "20", types)
        print(f"   {types:<40} dots={d:>3} lines={e:>3}")

    print("\n4. GRADE MIX in the default view at ch40\n")
    r = client.get(f"{base}/graph", params={"n": 40, "cast": "20", "types": "Character"})
    edges = r.json()["elements"]["edges"]
    stated = sum(1 for e in edges if e["data"].get("grade") == "STATED")
    inferred = sum(1 for e in edges if e["data"].get("grade") == "INFERRED")
    same_as = [e for e in edges if e["data"].get("relation") == "SAME_AS"]
    print(f"   STATED   {stated}")
    print(f"   INFERRED {inferred}")
    share = (inferred / len(edges) * 100) if edges else 0.0
    print(f"   INFERRED share: {share:.1f}%")
    print(f"   SAME_AS served: {len(same_as)} "
          f"(all STATED: {all(e['data'].get('grade') == 'STATED' for e in same_as)})")
    print(f"   every edge has a quote: "
          f"{all(e['data'].get('quote') or e['data'].get('evidence_span') for e in edges)}")

    print("\n5. EGO ENDPOINT\n")
    r = client.get(f"{base}/graph", params={"n": 40, "cast": "20", "types": "Character"})
    first = r.json()["elements"]["nodes"][0]["data"]
    eid = int(first["id"])
    r = client.get(f"{base}/entity/{eid}/ego", params={"n": 40})
    print(f"   ego of {first['label']!r} at ch40 -> {r.status_code}")
    if r.status_code == 200:
        for nb in r.json()["neighbours"][:6]:
            q = (nb["quote"] or "")[:60]
            print(f"     {nb['relation']:<14} {nb['name']:<22} [{nb['grade']}] {q!r}")
    r = client.get(f"{base}/entity/999999/ego", params={"n": 40})
    print(f"   ego of a non-existent entity -> {r.status_code} (expect 404)")

    print("\n6. D3 -- the status count now goes through the fence\n")
    for n in (1, 10, 40):
        r = client.get(f"{base}/status", params={"n": n})
        print(f"   n={n:>3}: node_count={r.json()['node_count']}")
    print("   (v1 returned the same total at every chapter)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
