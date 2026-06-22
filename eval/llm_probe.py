"""Phase 7b ADDENDUM — a REVEAL-CHAPTER-GRADED identity probe (sweep, not single-shot).

The 7b go/no-go gate used one easy clue (Wren==Caelum, stated in a single sentence) —
every config solved it, so the model pick rested on size reasoning, not evidence. This
addendum makes the probe measure the thing 7c actually depends on: an identity edge's
``revealed_chapter`` will be the SMALLEST k at which the model can conclude the identity
from chapters 1..k ONLY (confirmed-only semantics). So the failure that matters is not
"does the model ever agree" — it is "does it flip to YES at the RIGHT chapter, or one
chapter EARLY on a partial clue." An eager-but-correct model produces a right edge with a
spoiler-shifted reveal: it blooms a chapter too soon. A yes/no scorer cannot see that; an
incremental sweep can.

Method: for each case, sweep k = 1..(gold_reveal + 1, capped at the last chapter), feeding
ONLY chapters 1..k (reveal-respecting — no later-chapter clue leaks into an earlier-k
probe). Record ``first_yes_k`` = the smallest k at which the model asserts the identity,
and score it against the gold reveal chapter:
    EXACT  first_yes_k == gold   (ideal)
    EARLY  first_yes_k <  gold   (spoiler-shifted reveal — counts AGAINST the model here)
    LATE   first_yes_k >  gold   (under-reveal; less harmful, noted)
    MISS   never yes in range
For the negative control: PASS = never yes at any k; FAIL = any yes (over-merge).

Identity is probed PER CANDIDATE PAIR (the form 7c uses: propose a pair from co-occurring
entities, ask the LLM to confirm from 1..k), via the strict-JSON ``same_entity`` schema:
``{"same_entity": [["A","B"]]}`` if same, ``{"same_entity": []}`` if not/undetermined.
The transmigration case has no second NAME, so it uses a boolean schema; the sweep logic
is identical. tok/s is RE-MEASURED from this run (the sweep changes the call count, so 7b's
numbers are not carried forward). Pure stdlib (urllib) — runs under either venv. LotM stays
local; CC0 sample only. NO 7c pipeline, NO identity edge is written to the DB.

    .venv\\Scripts\\python eval\\llm_probe.py            # both finalists, base prompt
    .venv\\Scripts\\python eval\\llm_probe.py --cite      # the ONE prompt improvement
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "samples" / "the-hollow-crown"
CHAPTERS = ["ch01.txt", "ch02.txt", "ch03.txt", "ch04.txt"]
HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").replace("http://", "")

# Finalists at their working configs (model, device label, num_gpu).
FINALISTS: list[tuple[str, str, int]] = [
    ("llama3.2:3b", "GPU", 99),  # fast fallback candidate — fully offloads on the 4 GB card
    ("qwen2.5:7b", "CPU", 0),    # current primary candidate — system RAM, leaves VRAM free
]

SYSTEM_PAIR = (
    "You are a precise information-extraction tool for fiction. Considering ONLY the passage "
    "given, decide whether the two named entities refer to the SAME single person — the text "
    "states or clearly implies one IS the other (a secret identity, alias, or true name). If "
    "the passage does not let you conclude this, they are NOT the same. Two different people "
    "who merely interact, are related, or are allies are NOT the same. Output ONLY strict "
    'JSON, no prose: {"same_entity": [["A","B"]]} if they are one person, else '
    '{"same_entity": []}.'
)
SYSTEM_PAIR_CITE = (
    "You are a precise information-extraction tool for fiction. Considering ONLY the passage "
    "given, decide whether the two named entities refer to the SAME single person (a secret "
    "identity, alias, or true name). You may answer YES only if you can quote the exact clause "
    "from THIS passage that states or clearly implies it; if you cannot quote such a clause, "
    "the answer is NO. People who merely interact, are related, or are allies are NOT the same. "
    'Output ONLY strict JSON: {"same_entity": [{"names":["A","B"],"clue":"<exact quote>"}]} if '
    'they are one person, else {"same_entity": []}.'
)
SYSTEM_TRANSMIG = (
    "You are a precise literary-analysis tool. Considering ONLY the passage given, decide "
    "whether the text states or clearly implies the protagonist's soul or consciousness "
    "ORIGINATES from another world or a past life — an outside soul now inhabits this body "
    "(transmigration or reincarnation). Visions, dreams, or unexplained memories alone are NOT "
    "enough; you need text implying an outside soul in this body. Output ONLY strict JSON: "
    '{"transmigration": true|false, "evidence": "<exact quote or empty>"}.'
)
SYSTEM_TRANSMIG_CITE = (
    "You are a precise literary-analysis tool. Considering ONLY the passage given, decide "
    "whether the text states or clearly implies the protagonist's soul ORIGINATES from another "
    "world or a past life (an outside soul now in this body). Answer true ONLY if you can quote "
    "the exact clause that implies an OUTSIDE SOUL in this body; visions or dreams alone are NOT "
    "enough and must be answered false. Output ONLY strict JSON: "
    '{"transmigration": true|false, "evidence": "<exact quote, required if true>"}.'
)


def _passage(k: int) -> str:
    parts = [(SAMPLE_DIR / c).read_text(encoding="utf-8").strip() for c in CHAPTERS[:k]]
    return "\n\n".join(parts)


def _groups_from(obj: Any) -> list[list[str]]:
    """Normalize both the plain and the --cite cited ``same_entity`` schemas to lists."""
    if not isinstance(obj, dict):
        return []
    raw = obj.get("same_entity", [])
    groups: list[list[str]] = []
    for g in raw if isinstance(raw, list) else []:
        names = g.get("names", []) if isinstance(g, dict) else g
        if isinstance(names, (list, tuple)):
            groups.append([str(x).strip().lower() for x in names])
    return groups


def _pair_asserted(obj: Any, a: str, b: str) -> bool:
    return any(any(a in n for n in g) and any(b in n for n in g) for g in _groups_from(obj))


@dataclass
class Case:
    key: str
    label: str
    kind: str               # "pair" | "transmig" | "negative"
    gold: int | None        # gold reveal chapter (None for the negative control)
    a: str = ""             # pair token A (lowercased substring)
    b: str = ""             # pair token B
    ask: str = ""           # the human-readable pair phrasing in the prompt


CASES: list[Case] = [
    Case("C1", "Wren==Caelum", "pair", 2, "wren", "caelum", "'Wren' and 'Prince Caelum'"),
    Case("C2", "Sparrow==Veris", "pair", 3, "sparrow", "veris",
         "'the Gray Sparrow' and 'Lady Veris'"),
    Case("C3", "Transmigration", "transmig", 4),
    Case("C4", "Veris!=Dunmore", "negative", None, "veris", "dunmore",
         "'Lady Veris' and 'Ser Dunmore'"),
]


def _ceiling(case: Case) -> int:
    """Sweep up to gold+1 (one chapter of rope to expose an EARLY flip), capped at the end."""
    if case.gold is None:
        return len(CHAPTERS)
    return min(len(CHAPTERS), case.gold + 1)


@dataclass
class Probe:
    yes: bool = False
    tps: float = 0.0
    raw: str = ""
    error: str = ""


def _post(payload: dict[str, object], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(
        f"http://{HOST}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]


def probe_at_k(model: str, num_gpu: int, case: Case, k: int, cite: bool) -> Probe:
    if case.kind == "transmig":
        system = SYSTEM_TRANSMIG_CITE if cite else SYSTEM_TRANSMIG
        user = ("Does the text imply the protagonist is a transmigrator or reincarnation — an "
                "outside soul placed into this body — rather than just dreams or memories? "
                "JSON only.")
    else:
        system = SYSTEM_PAIR_CITE if cite else SYSTEM_PAIR
        user = f"Are {case.ask} the same person? JSON only."
    payload = {
        "model": model,
        "system": system,
        "prompt": f"PASSAGE (chapters 1..{k}):\n{_passage(k)}\n\n{user}",
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_gpu": num_gpu, "num_ctx": 4096, "seed": 7},
    }
    p = Probe()
    try:
        data = _post(payload, timeout=900)
        p.raw = str(data.get("response", ""))
        eval_tokens = int(data.get("eval_count", 0) or 0)
        eval_ns = float(data.get("eval_duration", 0) or 0)
        if eval_ns > 0:
            p.tps = eval_tokens / (eval_ns / 1e9)
        try:
            obj = json.loads(p.raw)
        except (json.JSONDecodeError, TypeError):
            obj = None
        if case.kind == "transmig":
            p.yes = isinstance(obj, dict) and obj.get("transmigration") is True
        else:
            p.yes = _pair_asserted(obj, case.a, case.b)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        p.error = type(exc).__name__
    return p


@dataclass
class CaseResult:
    first_yes_k: int | None = None
    verdict: str = ""
    per_k: list[tuple[int, bool]] = field(default_factory=list)
    tps_samples: list[float] = field(default_factory=list)
    note: str = ""


def sweep_case(model: str, num_gpu: int, case: Case, cite: bool) -> CaseResult:
    res = CaseResult()
    for k in range(1, _ceiling(case) + 1):
        p = probe_at_k(model, num_gpu, case, k, cite)
        if p.error:
            res.note = f"err@k{k}:{p.error}"
            break
        if p.tps:
            res.tps_samples.append(p.tps)
        res.per_k.append((k, p.yes))
        if p.yes and res.first_yes_k is None:
            res.first_yes_k = k
            if case.kind != "negative":
                break  # first flip is all the temporal score needs for a positive
    res.verdict = _verdict(case, res.first_yes_k)
    return res


def _verdict(case: Case, first_yes_k: int | None) -> str:
    if case.kind == "negative":
        return "FAIL" if first_yes_k is not None else "PASS"
    if first_yes_k is None:
        return "MISS"
    assert case.gold is not None
    if first_yes_k == case.gold:
        return "EXACT"
    return "EARLY" if first_yes_k < case.gold else "LATE"


@dataclass
class ModelReport:
    model: str
    dev: str
    results: dict[str, CaseResult] = field(default_factory=dict)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cite", action="store_true",
                    help="prompt improvement: require a quoted clue before asserting YES")
    args = ap.parse_args()

    try:
        urllib.request.urlopen(f"http://{HOST}/api/version", timeout=30).read()
    except (urllib.error.URLError, TimeoutError):
        print(f"error: no Ollama server at {HOST}. Start it: tools/ollama/ollama serve")
        return 2

    mode = "CITED prompt (clue required before YES)" if args.cite else "base prompt"
    print(f"Reveal-chapter-graded identity probe -- the-hollow-crown -- {mode} -- {HOST}")
    golds = "  ".join(f"{c.key}:{c.label} gold=ch{c.gold}" if c.gold else f"{c.key}:{c.label} (neg)"
                      for c in CASES)
    print(f"sweep k=1..(gold+1), reveal-respecting; first_yes_k vs gold.\n{golds}\n")

    reports: list[ModelReport] = []
    for model, dev, num_gpu in FINALISTS:
        rep = ModelReport(model, dev)
        for case in CASES:
            rep.results[case.key] = sweep_case(model, num_gpu, case, args.cite)
        reports.append(rep)

    # --- table: model x case -> first_yes_k / gold / verdict -------------------------
    hdr = f"{'model':<13}{'dev':<5}"
    for c in CASES:
        hdr += f"{c.key + '(g' + (str(c.gold) if c.gold else '-') + ')':>14}"
    hdr += f"{'tok/s':>8}{'summary':>26}"
    print(hdr)
    print("-" * len(hdr))
    for rep in reports:
        line = f"{rep.model:<13}{rep.dev:<5}"
        toks: list[float] = []
        exacts = earlies = lates = misses = 0
        control = "?"
        for c in CASES:
            r = rep.results[c.key]
            toks += r.tps_samples
            fy = str(r.first_yes_k) if r.first_yes_k is not None else "-"
            cell = f"{fy}:{r.verdict}"
            line += f"{cell:>14}"
            if c.kind == "negative":
                control = r.verdict
            elif r.verdict == "EXACT":
                exacts += 1
            elif r.verdict == "EARLY":
                earlies += 1
            elif r.verdict == "LATE":
                lates += 1
            else:
                misses += 1
        tps = sum(toks) / len(toks) if toks else 0.0
        summ = f"{exacts}E/{earlies}early/{lates}late/{misses}miss ctrl={control}"
        line += f"{tps:>8.1f}{summ:>26}"
        print(line)
    print("-" * len(hdr))
    print("cell = first_yes_k:VERDICT.  EXACT=flip at gold (ideal)  EARLY=flip before gold "
          "(spoiler-shift)  LATE=after  MISS=never.  ctrl PASS=never merged, FAIL=over-merged.\n")

    # --- transparency: per-k flip trace ----------------------------------------------
    for rep in reports:
        print(f"### {rep.model} ({rep.dev})")
        for c in CASES:
            r = rep.results[c.key]
            trace = " ".join(f"k{k}={'Y' if y else 'n'}" for k, y in r.per_k)
            goldtxt = f"gold=ch{c.gold}" if c.gold is not None else "negative"
            extra = f"  [{r.note}]" if r.note else ""
            print(f"  {c.key} {c.label:<16} {goldtxt:<12} first_yes={r.first_yes_k} "
                  f"-> {r.verdict}   trace: {trace}{extra}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
