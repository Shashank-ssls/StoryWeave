"""Pytest bootstrap.

HuggingFace reads HF_HOME / symlink settings at *import* time, and ``importorskip
("gliner")`` inside a test imports HF before any app code runs. conftest is imported
before test collection, so we pin the model cache to the project drive (F:) here —
never C: (CLAUDE.md env discipline) — guaranteeing it's set before the first HF import.
"""

from __future__ import annotations

import os
from pathlib import Path

_HF_CACHE = Path(__file__).resolve().parents[1] / ".hf-cache"
_HF_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(_HF_CACHE))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
