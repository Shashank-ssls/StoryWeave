"""Phase 8 Part B: the background analysis runner (`api/jobs.py`).

The runner shells out to `.venv-ml` for the heavy NLP, so the API process stays on the
light venv. These tests exercise the in-memory state registry and the graceful-degrade
path WITHOUT a real subprocess — when `.venv-ml` is absent the run records an error and
the API floor (the already-ingested chapters) is untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storyweave.api import jobs


def setup_function() -> None:
    jobs._jobs.clear()


def test_status_is_none_before_start() -> None:
    assert jobs.get_status("ghost") is None


def test_set_and_get_status_roundtrip() -> None:
    jobs._set("w", "extracting", "ch 1/4")
    st = jobs.get_status("w")
    assert st is not None
    assert (st.state, st.detail) == ("extracting", "ch 1/4")
    # get_status returns a copy, not the live object.
    assert jobs.get_status("w") is not st


def test_run_errors_when_ml_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORYWEAVE_ML_PYTHON", str(Path("nonexistent") / "python.exe"))
    jobs._run("w", db_path=":memory:")
    st = jobs.get_status("w")
    assert st is not None
    assert st.state == "error"
    assert ".venv-ml" in st.detail or "ML environment" in st.detail


def test_ml_python_honours_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORYWEAVE_ML_PYTHON", "C:/custom/py.exe")
    assert jobs.ml_python() == Path("C:/custom/py.exe")
