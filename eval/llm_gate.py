"""Phase 7b — the LLM go/no-go gate (NOT a feature).

Tests whether a local LLM can do the Tier-3 identity-inference task *in miniature*,
on BOTH viable paths for a GTX 1650 (4 GB) + 16 GB RAM box, and prints a go/no-go
matrix (config -> loads? -> JSON? -> correct? -> tokens/sec -> VRAM offload). The
deliverable is a DECISION, not pipeline code — no Tier-3 logic is wired here.

Runner: Ollama (no-installer zip under tools/, models cached to F: via OLLAMA_MODELS).
Ollama bundles CUDA runners (auto partial-offload on 4 GB) and reports eval timing,
so tokens/sec is measured, not guessed. We force CPU with ``num_gpu=0`` and let the
GPU offload as many layers as fit with ``num_gpu=99``.

Probe: two short chapters of the CC0 sample where Wren is clued to be Prince Caelum;
the model must emit STRICT JSON ``{"same_entity": [["Wren","Caelum"]]}``. Correct =
some group contains both a Wren-variant and a Caelum-variant. Pure stdlib (urllib),
so it runs under either venv. LotM stays local — sample only.

    .venv\\Scripts\\python eval\\llm_gate.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "data" / "samples" / "the-hollow-crown"
HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").replace("http://", "")

SYSTEM = (
    "You are a precise information-extraction tool for fiction. Read the passage and "
    "decide whether two or more distinct NAMES refer to the same single entity (one "
    "person). Output ONLY strict JSON, no prose, of the form "
    '{"same_entity": [["NameA", "NameB"]]} where each inner list groups names that '
    'denote one entity. If no names co-refer, output {"same_entity": []}.'
)

# Configs to probe: (model, device label, num_gpu). num_gpu=0 -> CPU; 99 -> offload
# as many layers as fit in VRAM (Ollama caps to the 4 GB card).
CONFIGS: list[tuple[str, str, int]] = [
    ("llama3.2:3b", "GPU", 99),  # GPU path: 3-4B Q4 on the 4 GB card
    ("qwen2.5:7b", "CPU", 0),    # CPU path: 7-8B Q4 in system RAM
    ("llama3.2:3b", "CPU", 0),   # completeness: small model on CPU
    ("qwen2.5:7b", "GPU", 99),   # 7B on 4 GB -> partial offload (show the OOM-ish split)
]


@dataclass
class ProbeResult:
    loaded: bool = False
    json_ok: bool = False
    correct: bool = False
    tokens_per_sec: float = 0.0
    eval_tokens: int = 0
    total_seconds: float = 0.0
    vram_fraction: float = 0.0  # share of model weights resident in VRAM
    error: str = ""


def _passage() -> str:
    parts = []
    for name in ("ch01.txt", "ch02.txt"):
        parts.append((SAMPLE_DIR / name).read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


def _post(path: str, payload: dict[str, object], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(
        f"http://{HOST}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]


def _ps_vram_fraction(model: str) -> float:
    try:
        req = urllib.request.Request(f"http://{HOST}/api/ps", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for m in data.get("models", []):
            if m.get("name", "").startswith(model) or m.get("model", "").startswith(model):
                size = float(m.get("size", 0)) or 1.0
                return float(m.get("size_vram", 0)) / size
    except (urllib.error.URLError, ValueError, KeyError):
        pass
    return 0.0


def _grade(text: str) -> tuple[bool, bool]:
    """Return (json_ok, correct)."""
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return False, False
    groups = obj.get("same_entity", []) if isinstance(obj, dict) else []
    for g in groups if isinstance(groups, list) else []:
        names = {str(x).strip().lower() for x in g} if isinstance(g, (list, tuple)) else set()
        has_wren = any("wren" in n for n in names)
        has_caelum = any("caelum" in n for n in names)
        if has_wren and has_caelum:
            return True, True
    return True, False


def run_probe(model: str, num_gpu: int, passage: str) -> ProbeResult:
    res = ProbeResult()
    prompt = (
        f"PASSAGE:\n{passage}\n\n"
        "Which names in this passage refer to the same entity? Respond with JSON only."
    )
    payload = {
        "model": model,
        "system": SYSTEM,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_gpu": num_gpu, "num_ctx": 4096, "seed": 7},
    }
    try:
        t0 = time.time()
        data = _post("/api/generate", payload, timeout=900)
        res.total_seconds = time.time() - t0
        res.loaded = True
        text = str(data.get("response", ""))
        res.eval_tokens = int(data.get("eval_count", 0) or 0)
        eval_ns = float(data.get("eval_duration", 0) or 0)
        if eval_ns > 0:
            res.tokens_per_sec = res.eval_tokens / (eval_ns / 1e9)
        res.vram_fraction = _ps_vram_fraction(model)
        res.json_ok, res.correct = _grade(text)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        res.error = type(exc).__name__
    return res


def main() -> int:
    try:
        urllib.request.urlopen(f"http://{HOST}/api/version", timeout=5).read()
    except (urllib.error.URLError, TimeoutError):
        print(f"error: no Ollama server at {HOST}. Start it: tools/ollama/ollama serve")
        return 2

    passage = _passage()
    print(f"LLM go/no-go gate -- probe = Wren==Caelum identity on the CC0 sample ({HOST})")
    cols = ("model", "dev", "load", "json", "corr", "tok/s", "tot s", "vram%")
    print(f"{cols[0]:<14}{cols[1]:<5}{cols[2]:>6}{cols[3]:>6}{cols[4]:>6}"
          f"{cols[5]:>9}{cols[6]:>8}{cols[7]:>7}")
    print("-" * 61)
    any_go = False
    for model, dev, num_gpu in CONFIGS:
        r = run_probe(model, num_gpu, passage)
        go = r.loaded and r.json_ok and r.correct
        any_go = any_go or go
        load = "yes" if r.loaded else (r.error or "no")
        print(
            f"{model:<14}{dev:<5}{load:>6}{('yes' if r.json_ok else 'no'):>6}"
            f"{('YES' if r.correct else 'no'):>6}{r.tokens_per_sec:>9.1f}"
            f"{r.total_seconds:>8.1f}{r.vram_fraction * 100:>6.0f}%"
        )
    print("-" * 61)
    print("GO" if any_go else "NO-GO", "-- at least one config produced correct identity JSON"
          if any_go else "-- no config solved the probe")
    return 0 if any_go else 1


if __name__ == "__main__":
    sys.exit(main())
