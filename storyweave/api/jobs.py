"""Background analysis runner for in-app ingest (Phase 8 Part B).

In-app ingest creates the work + chapters in-process (Phase-1 ingest is ML-free), then
this module runs the heavy NLP (`extract` → `relate`) by SHELLING OUT to the `.venv-ml`
CLI. The API process therefore imports no ML and stays on the light venv (architecture
rule). Status is a tiny in-memory registry the frontend polls; nothing here writes SQL
(the subprocess uses the existing repository via the CLI).
"""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# state: queued -> extracting -> relating -> ready | error
_STEPS = (("extract", "extracting"), ("relate", "relating"))


def ml_python() -> Path:
    """Path to the .venv-ml interpreter (override with STORYWEAVE_ML_PYTHON)."""
    override = os.environ.get("STORYWEAVE_ML_PYTHON")
    if override:
        return Path(override)
    return REPO_ROOT / ".venv-ml" / "Scripts" / "python.exe"


@dataclass
class Analysis:
    state: str = "queued"
    detail: str = ""


_lock = threading.Lock()
_jobs: dict[str, Analysis] = {}


def get_status(slug: str) -> Analysis | None:
    with _lock:
        cur = _jobs.get(slug)
        return Analysis(cur.state, cur.detail) if cur else None


def _set(slug: str, state: str, detail: str = "") -> None:
    with _lock:
        _jobs[slug] = Analysis(state, detail)


def _run(slug: str, db_path: str) -> None:
    py = ml_python()
    if not py.exists():
        _set(slug, "error", "ML environment (.venv-ml) not found — run extraction via the CLI")
        return
    for step, label in _STEPS:
        _set(slug, label)
        try:
            proc = subprocess.run(
                [str(py), "-m", "storyweave.cli.main", step, slug, "--db", db_path],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=1200,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:  # pragma: no cover - env-dependent
            _set(slug, "error", f"{step} failed: {exc}")
            return
        if proc.returncode != 0:
            _set(slug, "error", (proc.stderr or proc.stdout or f"{step} failed").strip()[-280:])
            return
    _set(slug, "ready")


def start_analysis(slug: str, db_path: str) -> None:
    """Launch extract→relate in a daemon thread; the API returns immediately."""
    _set(slug, "queued")
    threading.Thread(target=_run, args=(slug, db_path), daemon=True).start()
