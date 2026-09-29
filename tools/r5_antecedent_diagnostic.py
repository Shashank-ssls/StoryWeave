"""R5 diagnostic: how much would a "named antecedent in context" rule buy?

    .\\dev.ps1
    python tools/r5_antecedent_diagnostic.py

**DIAGNOSTIC ONLY. Nothing here ships, and nothing here is used to grade an edge.**

R5's STATED rule requires a label of BOTH participants inside the verbatim quote, so a
proposal whose head is only "She" grades INFERRED and is stored but never served. A
plausible future relaxation is: accept it as STATED if the pronoun's entity is NAMED in
the two sentences of context the model was shown.

This measures how many INFERRED proposals that rule would promote. It is reported so the
decision can be made on a number rather than on intuition, and it is deliberately NOT
implemented in the validator: promoting on context would weaken retrofit rule 4 (the
quote must carry the claim), and that trade deserves its own phase and its own
pre-registration.

Reads `evidence/retrofit/R5_proposals.jsonl` and the R5 database. Writes nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storyweave.db.repository import Repository  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "retrofit" / "ninth_house_r5.db"
DEFAULT_DUMP = REPO_ROOT / "evidence" / "retrofit" / "R5_proposals.jsonl"
SLUG = "the-ninth-house"


def labels_for(repo: Repository, work_id: int) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for node in repo.list_nodes(work_id):
        if node.id is None:
            continue
        names = [node.name, *(lab.label for lab in repo.list_entity_labels(node.id))]
        out[node.id] = sorted({n for n in names if n}, key=len, reverse=True)
    return out


def named_in(text: str, names: list[str]) -> str | None:
    lowered = text.lower()
    for name in names:
        if re.search(rf"(?<!\w){re.escape(name.lower())}(?!\w)", lowered):
            return name
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    ap.add_argument("--slug", default=SLUG)
    args = ap.parse_args(argv)

    repo = Repository(args.db)
    work = repo.get_work_by_slug(args.slug)
    assert work is not None and work.id is not None
    by_name: dict[str, int] = {}
    for node in repo.list_nodes(work.id):
        if node.id is not None:
            by_name.setdefault(node.name.lower(), node.id)
            for lab in repo.list_entity_labels(node.id):
                by_name.setdefault(lab.label.lower(), node.id)
    labels = labels_for(repo, work.id)
    repo.close()

    rows = [json.loads(line) for line in args.dump.open(encoding="utf-8")]
    inferred = [r for r in rows if r["ok"] and r["grade"] == "INFERRED"]

    print("=" * 78)
    print("R5 DIAGNOSTIC — 'named antecedent within the 2 context sentences'")
    print("=" * 78)
    print(f"\naccepted proposals in the dump : {sum(1 for r in rows if r['ok'])}")
    print(f"of those, INFERRED             : {len(inferred)}")

    promoted: list[dict[str, str]] = []
    reasons: Counter[str] = Counter()
    for r in inferred:
        quote = r["quote"]
        ctx = r.get("context") or ""
        missing = []
        for role in ("head", "tail"):
            nid = by_name.get(str(r[role]).lower())
            if nid is None:
                missing.append(f"{role}:unresolved")
                continue
            if named_in(quote, labels.get(nid, [])) is None:
                missing.append(role)
        if not missing:
            reasons["already had both names (grade set by cue)"] += 1
            continue
        # Would the missing side be recoverable from the context?
        recoverable = True
        for role in missing:
            if ":" in role:
                recoverable = False
                break
            nid = by_name.get(str(r[role]).lower())
            if nid is None or named_in(ctx, labels.get(nid, [])) is None:
                recoverable = False
                break
        if recoverable:
            promoted.append(r)
            reasons["WOULD PROMOTE (antecedent named in context)"] += 1
        else:
            reasons["not recoverable from context either"] += 1

    print(f"\n{'outcome':<48} {'n':>5}")
    print("-" * 56)
    for reason, n in reasons.most_common():
        print(f"{reason:<48} {n:>5}")

    print(f"\nWOULD BE PROMOTED TO STATED: {len(promoted)}")
    for r in promoted:
        print(f"\n  ch{r['chapter']:>2}  {r['head']} -{r['relation']}-> {r['tail']}")
        print(f"      quote  : {r['quote'][:110]!r}")
        print(f"      context: {(r.get('context') or '')[:110]!r}")
    print("\nNOT SHIPPED. Diagnostic only — see this tool's docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
