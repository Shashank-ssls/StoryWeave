"""Phase 7c — the LIVE reveal-accuracy check (informational, NON-BLOCKING).

The production analog of the Phase-7b addendum sweep: it drives the REAL
:class:`~storyweave.nlp.identity.LlmIdentityModel` (same prompt, same citation gate as
the pipeline) over the CC0 sample and reports, per proven identity, the smallest
chapter k at which the model confirms it WITH a verifiable in-range citation —
``first_yes_k`` vs the gold reveal chapter (EXACT / EARLY / LATE / MISS) — plus the
negative control (which must never confirm). This is how you'd catch a real model
regressing on a real novel; it is a REPORT, never a green-gating test (the permanent
regressions live in tests/test_identity.py and use a fake model).

Requires the flag on + a running runner; prints a notice and exits cleanly otherwise.
LotM stays local — sample only. Ollama is stopped at the end of the session.

    .venv\\Scripts\\python eval\\identity_eval.py [--model llama3.2:3b]
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

from storyweave.config import Settings
from storyweave.nlp.identity import LlmIdentityModel, citation_in_range

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "samples" / "the-hollow-crown"

# (entity A, entity B, target relation, gold reveal chapter). Negative control: gold=None.
TARGETS: list[tuple[str, str, str | None, int | None]] = [
    ("Wren", "Prince Caelum", "SECRET_IDENTITY", 2),
    ("the Gray Sparrow", "Lady Veris", "ALIAS", 3),
    ("Wren", "Prince Caelum", "TRANSMIGRATED_INTO", 4),
    ("Lady Veris", "Ser Dunmore", None, None),  # distinct allies — must never confirm
]
NUM_CHAPTERS = 4


def _fed(k: int) -> str:
    parts = [
        (SAMPLE_DIR / f"ch{n:02d}.txt").read_text(encoding="utf-8").strip()
        for n in range(1, k + 1)
    ]
    return "\n\n".join(parts)


def _verdict(first_yes_k: int | None, gold: int | None) -> str:
    if gold is None:  # negative control
        return "FAIL(over-merge)" if first_yes_k is not None else "PASS"
    if first_yes_k is None:
        return "MISS"
    return "EXACT" if first_yes_k == gold else ("EARLY" if first_yes_k < gold else "LATE")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model", default="qwen2.5:7b",
        help="runner model id (7c identity primary; pass llama3.2:3b for the speed fallback)",
    )
    args = ap.parse_args()

    settings = Settings(llm_enabled=True, llm_model=args.model)
    base = (settings.llm_base_url or "").replace("/v1", "")
    try:
        urllib.request.urlopen(f"{base}/api/version", timeout=30).read()
    except (urllib.error.URLError, TimeoutError, ValueError):
        print(f"notice: no runner reachable at {settings.llm_base_url} — skipping live check.")
        return 0

    model = LlmIdentityModel(settings)
    print(f"Live identity reveal-accuracy -- the-hollow-crown -- model={args.model}")
    print(f"{'pair':<34}{'target':<20}{'gold':>5}{'first_yes':>11}{'verdict':>18}")
    print("-" * 88)

    for a, b, relation, gold in TARGETS:
        ceiling = NUM_CHAPTERS if gold is None else min(NUM_CHAPTERS, gold + 1)
        first_yes_k: int | None = None
        for k in range(1, ceiling + 1):
            fed = _fed(k)
            v = model.infer(a, b, fed, k)
            confirmed = (
                v.same
                and v.relation is not None
                and (relation is None or v.relation == relation)
                and citation_in_range(v.clue, fed)
            )
            if confirmed:
                first_yes_k = k
                break
        target_lbl = relation or "(NOT same)"
        gold_lbl = "-" if gold is None else str(gold)
        fy = "-" if first_yes_k is None else str(first_yes_k)
        print(f"{a + ' = ' + b:<34}{target_lbl:<20}{gold_lbl:>5}{fy:>11}"
              f"{_verdict(first_yes_k, gold):>18}")
    print("-" * 88)
    print("Strict scoring requires the EXACT relation subtype. The two soft spots are "
          "labeling, not timing/safety:")

    # Relation-AGNOSTIC identity timing: when is the pair first confirmed to be one
    # identity at all (any Tier-3 label) with a valid citation? This isolates reveal
    # TIMING + the negative control from the model's relation-subtype labeling.
    print(f"\n{'pair (identity-presence, any relation)':<40}{'gold':>6}"
          f"{'first_yes':>11}{'verdict':>10}")
    print("-" * 67)
    seen: set[frozenset[str]] = set()
    for a, b, _rel, _gold in TARGETS:
        if frozenset({a, b}) in seen:
            continue
        seen.add(frozenset({a, b}))
        # For a pair, the identity "gold" is the earliest gold among its target relations.
        pair_gold = min(
            (g for x, y, _r, g in TARGETS if frozenset({x, y}) == frozenset({a, b}) and g),
            default=None,
        )
        ceiling = NUM_CHAPTERS if pair_gold is None else min(NUM_CHAPTERS, pair_gold + 1)
        first_yes_k = None
        for k in range(1, ceiling + 1):
            fed = _fed(k)
            v = model.infer(a, b, fed, k)
            if v.same and v.relation is not None and citation_in_range(v.clue, fed):
                first_yes_k = k
                break
        gold_lbl = "-" if pair_gold is None else str(pair_gold)
        fy = "-" if first_yes_k is None else str(first_yes_k)
        print(f"{a + ' = ' + b:<40}{gold_lbl:>6}{fy:>11}{_verdict(first_yes_k, pair_gold):>10}")
    print("-" * 67)
    print("EXACT = blooms at the gold chapter (ideal); EARLY = spoiler-shifted; "
          "negative control must be PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
