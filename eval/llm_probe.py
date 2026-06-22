"""Phase 7b ADDENDUM — a *graded* identity probe that actually discriminates 3B vs 7B.

The 7b go/no-go gate (``eval/llm_gate.py``) used a single easy clue (Wren==Caelum,
stated in one sentence) — every config solved it, so the model choice rested on size
reasoning, not accuracy evidence. This probe fixes that: four graded cases, each with a
gold label and a reveal-respecting chapter window, run on BOTH finalists at their
working configs (GPU llama3.2:3b, CPU qwen2.5:7b). The deliverable is a DECISION backed
by a table — still NO 7c pipeline, NO identity edges written to the DB.

The cases (gold in parens):
  1. Wren == Prince Caelum                  (MERGE)  — easy positive, the baseline.
  2. Gray Sparrow == Lady Veris             (MERGE)  — the spymistress alias.
  3. transmigration / outside-soul          (TRUE)   — the subtlest inference.
  4. NEGATIVE CONTROL: no false merges       (NONE)   — punishes over-merging.

The negative control is the real discriminator: case 4 grades the FULL ch1-4 grouping
and FAILS if the model merges any two *distinct* people (e.g. Veris≠Maela, Caelum≠Maela,
Wren≠Dunmore). A model that over-merges to look clever is punished here. Correct
positives (Wren=Caelum, Sparrow=Veris) are same-identity surfaces and never trip it.

Reveal discipline (rule #1): each case is fed only the chapters where its fact is
knowable — case 1 sees ch1-2 (Caelum named ch2), case 2 sees ch1-3 (alias stated ch3),
cases 3/4 see ch1-4. No later-chapter clue leaks into an earlier probe.

Pure stdlib (urllib) so it runs under either venv. LotM stays local — CC0 sample only.

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
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "samples" / "the-hollow-crown"
HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").replace("http://", "")

# Finalists at their working configs (model, device label, num_gpu).
FINALISTS: list[tuple[str, str, int]] = [
    ("llama3.2:3b", "GPU", 99),  # fast fallback candidate — fully offloads on the 4 GB card
    ("qwen2.5:7b", "CPU", 0),    # current primary candidate — system RAM, leaves VRAM free
]

# --- canonical identity map (the ground truth for the negative control) --------------
# Each distinct PERSON gets a letter. Two surface names with the SAME letter are the
# same person (a legal merge); two names with DIFFERENT letters are distinct (a false
# merge if grouped together). "wren"/"caelum" -> A and "veris"/"sparrow" -> B are the
# only legal cross-surface merges in the sample.
TOKEN_CANON: dict[str, str] = {
    "wren": "A", "caelum": "A",
    "veris": "B", "sparrow": "B",
    "maela": "C",
    "dunmore": "D",
    "halvard": "E",
}

SYSTEM_GROUP = (
    "You are a precise information-extraction tool for fiction. Read the passage and "
    "group together the distinct NAMES that refer to the same single person. Two names "
    "co-refer ONLY if the text states or clearly implies they are one person (a secret "
    "identity, alias, or true name) — a parent and child, two friends, or two allies are "
    "DIFFERENT people and must NOT be grouped. Output ONLY strict JSON, no prose: "
    '{"same_entity": [["NameA","NameB"]]} where each inner list groups names denoting one '
    'person. Names with no co-reference are omitted. If none co-refer, output '
    '{"same_entity": []}.'
)
SYSTEM_GROUP_CITE = (
    "You are a precise information-extraction tool for fiction. Read the passage and "
    "group the distinct NAMES that refer to the same single person. Two names co-refer "
    "ONLY if the text states or clearly implies they are one person; a parent and child, "
    "two friends, or two allies are DIFFERENT people and must NOT be grouped. For EVERY "
    "group you MUST quote the exact clause from the passage that proves the co-reference; "
    "if you cannot quote such a clause, do NOT make the group. Output ONLY strict JSON: "
    '{"same_entity": [{"names": ["NameA","NameB"], "clue": "<exact quote>"}]}. '
    'If none co-refer, output {"same_entity": []}.'
)
SYSTEM_TRANSMIG = (
    "You are a precise literary-analysis tool. Decide whether the passage implies the "
    "protagonist's soul or consciousness originates from another world or a past life — "
    "i.e. an outside soul now inhabits this body (transmigration or reincarnation), as "
    "opposed to ordinary memories or dreams. Output ONLY strict JSON, no prose: "
    '{"transmigration": true|false, "evidence": "<short quote or empty>"}.'
)


def _passage(*chapters: str) -> str:
    parts = [(SAMPLE_DIR / c).read_text(encoding="utf-8").strip() for c in chapters]
    return "\n\n".join(parts)


# --- graders -------------------------------------------------------------------------
def _groups_from(obj: Any) -> list[list[str]]:
    """Normalize both the plain and the --cite cited grouping schemas to list[list[str]]."""
    if not isinstance(obj, dict):
        return []
    raw = obj.get("same_entity", [])
    groups: list[list[str]] = []
    for g in raw if isinstance(raw, list) else []:
        if isinstance(g, dict):  # cited schema: {"names": [...], "clue": "..."}
            names = g.get("names", [])
        else:
            names = g
        if isinstance(names, (list, tuple)):
            groups.append([str(x).strip().lower() for x in names])
    return groups


def _canon_letters(name: str) -> set[str]:
    return {letter for tok, letter in TOKEN_CANON.items() if tok in name}


def _has_pair(groups: list[list[str]], a: str, b: str) -> bool:
    return any(any(a in n for n in g) and any(b in n for n in g) for g in groups)


def grade_merge(a: str, b: str) -> Callable[[Any], bool]:
    """Positive case: pass iff some group contains both surface tokens a and b."""
    return lambda obj: _has_pair(_groups_from(obj), a, b)


def grade_no_false_merge(obj: Any) -> bool:
    """Negative control: pass iff NO group spans two distinct canonical identities."""
    for g in _groups_from(obj):
        letters: set[str] = set()
        for name in g:
            letters |= _canon_letters(name)
        if len(letters) > 1:  # a group mixing >=2 distinct people = a false merge
            return False
    return True


def grade_transmig(obj: Any) -> bool:
    return isinstance(obj, dict) and obj.get("transmigration") is True


@dataclass
class Case:
    key: str
    label: str
    chapters: tuple[str, ...]
    system: str            # base-prompt system (grouping cases swap to CITE under --cite)
    grader: Callable[[Any], bool]
    is_group: bool         # grouping cases honor --cite; transmig does not


CASES: list[Case] = [
    Case("C1", "Wren=Caelum", ("ch01.txt", "ch02.txt"),
         SYSTEM_GROUP, grade_merge("wren", "caelum"), True),
    Case("C2", "Sparrow=Veris", ("ch01.txt", "ch02.txt", "ch03.txt"),
         SYSTEM_GROUP, grade_merge("sparrow", "veris"), True),
    Case("C3", "Transmigration", ("ch01.txt", "ch02.txt", "ch03.txt", "ch04.txt"),
         SYSTEM_TRANSMIG, grade_transmig, False),
    Case("C4", "NegControl", ("ch01.txt", "ch02.txt", "ch03.txt", "ch04.txt"),
         SYSTEM_GROUP, grade_no_false_merge, True),
]

GROUP_PROMPT = "Which names in this passage refer to the same person? Respond with JSON only."
TRANSMIG_PROMPT = (
    "Does the text imply the protagonist is a transmigrator or reincarnation — an outside "
    "soul placed into this body — rather than just dreams or memories? Respond JSON only."
)


@dataclass
class Run:
    ok: bool = False
    correct: bool = False
    raw: str = ""
    parsed: Any = None
    tokens_per_sec: float = 0.0
    error: str = ""
    n_groups: int = 0
    contaminated: int = 0  # grouping groups that mix >=2 distinct identities (false merges)
    clean_merges: int = 0  # grouping groups of >=2 surfaces that are one identity


def _post(payload: dict[str, object], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(
        f"http://{HOST}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]


def run_case(model: str, num_gpu: int, case: Case, cite: bool) -> Run:
    run = Run()
    system = case.system
    user = TRANSMIG_PROMPT if not case.is_group else GROUP_PROMPT
    if case.is_group and cite:
        system = SYSTEM_GROUP_CITE
    payload = {
        "model": model,
        "system": system,
        "prompt": f"PASSAGE:\n{_passage(*case.chapters)}\n\n{user}",
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_gpu": num_gpu, "num_ctx": 4096, "seed": 7},
    }
    try:
        data = _post(payload, timeout=900)
        run.ok = True
        run.raw = str(data.get("response", ""))
        eval_tokens = int(data.get("eval_count", 0) or 0)
        eval_ns = float(data.get("eval_duration", 0) or 0)
        if eval_ns > 0:
            run.tokens_per_sec = eval_tokens / (eval_ns / 1e9)
        try:
            run.parsed = json.loads(run.raw)
        except (json.JSONDecodeError, TypeError):
            run.parsed = None
        run.correct = bool(run.parsed is not None and case.grader(run.parsed))
        if case.is_group and run.parsed is not None:
            groups = _groups_from(run.parsed)
            run.n_groups = len(groups)
            for g in groups:
                letters: set[str] = set()
                for name in g:
                    letters |= _canon_letters(name)
                if len(letters) > 1:
                    run.contaminated += 1
                elif len(g) >= 2 and len(letters) == 1:
                    run.clean_merges += 1
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        run.error = type(exc).__name__
    return run


@dataclass
class ModelReport:
    model: str
    dev: str
    runs: dict[str, Run] = field(default_factory=dict)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cite", action="store_true",
                    help="prompt improvement: require a quoted clue per merge")
    args = ap.parse_args()

    try:
        urllib.request.urlopen(f"http://{HOST}/api/version", timeout=30).read()
    except (urllib.error.URLError, TimeoutError):
        print(f"error: no Ollama server at {HOST}. Start it: tools/ollama/ollama serve")
        return 2

    mode = "CITED prompt (clue required per merge)" if args.cite else "base prompt"
    print(f"Graded identity probe -- the-hollow-crown -- {mode} -- {HOST}")
    print("cases: C1 Wren=Caelum(merge) C2 Sparrow=Veris(merge) "
          "C3 Transmigration(true) C4 NegControl(no false merge)\n")

    reports: list[ModelReport] = []
    for model, dev, num_gpu in FINALISTS:
        rep = ModelReport(model, dev)
        for case in CASES:
            rep.runs[case.key] = run_case(model, num_gpu, case, args.cite)
        reports.append(rep)

    # --- the table: model x case -> correct? -----------------------------------------
    hdr = f"{'model':<13}{'dev':<5}"
    for c in CASES:
        hdr += f"{c.key:>6}"
    hdr += f"{'tok/s':>8}{'ALL':>6}{'merge P':>9}"
    print(hdr)
    print("-" * len(hdr))
    for rep in reports:
        line = f"{rep.model:<13}{rep.dev:<5}"
        all_ok = True
        toks: list[float] = []
        clean = bad = 0
        for c in CASES:
            r = rep.runs[c.key]
            all_ok = all_ok and r.correct
            if r.tokens_per_sec:
                toks.append(r.tokens_per_sec)
            clean += r.clean_merges
            bad += r.contaminated
            mark = "OK" if r.correct else ("err" if r.error else "X")
            line += f"{mark:>6}"
        tps = sum(toks) / len(toks) if toks else 0.0
        denom = clean + bad
        prec = clean / denom if denom else 1.0
        line += f"{tps:>8.1f}{('YES' if all_ok else 'no'):>6}{prec:>8.2f}"
        print(line)
    print("-" * len(hdr))
    print("legend: OK=correct  X=wrong  err=no response.  merge P = clean merges / all "
          "proposed merges across C1/C2/C4 (a false merge in C4 lowers it).\n")

    # --- transparency: dump each model's actual answers ------------------------------
    for rep in reports:
        print(f"### {rep.model} ({rep.dev})")
        for c in CASES:
            r = rep.runs[c.key]
            verdict = "OK" if r.correct else ("ERR:" + r.error if r.error else "WRONG")
            chs = ",".join(x.replace(".txt", "").replace("ch", "") for x in c.chapters)
            print(f"  {c.key} {c.label:<15} ch[{chs}] -> {verdict}")
            if c.is_group:
                print(f"      groups={_groups_from(r.parsed)} "
                      f"(clean_merge={r.clean_merges} contaminated={r.contaminated})")
            else:
                print(f"      raw={r.raw.strip()[:200]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
