"""Phase 7b: the optional LLM path is OFF by default and provably inert (rules #4/#5).

These run in the light .venv with no LLM runner installed — the client is stdlib-only
and the disabled path never touches the network.
"""

from __future__ import annotations

import urllib.request

import pytest

from storyweave.config import Settings
from storyweave.nlp.llm import LlmClient, llm_available


def test_llm_disabled_by_default() -> None:
    """The shipped default makes no LLM available (zero outbound calls path)."""
    assert Settings().llm_enabled is False
    assert llm_available(Settings()) is False


def test_client_refuses_to_construct_when_disabled() -> None:
    """No client object can exist while disabled — so no socket can be opened."""
    with pytest.raises(RuntimeError, match="disabled"):
        LlmClient(Settings(llm_enabled=False))


def test_no_outbound_call_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hard proof: with the flag off, nothing in the gated path opens a connection."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network call attempted while llm_enabled=False")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    settings = Settings()  # default: disabled
    assert llm_available(settings) is False
    # A caller that correctly checks the gate never constructs a client or calls out.
    if llm_available(settings):  # pragma: no cover - never taken by default
        LlmClient(settings).complete_json("s", "u")


def test_available_only_when_enabled_and_configured() -> None:
    """Enabled requires a base_url + model; missing config keeps it unavailable."""
    assert llm_available(Settings(llm_enabled=True, llm_base_url=None)) is False
    assert llm_available(Settings(llm_enabled=True, llm_model=None)) is False
    assert (
        llm_available(
            Settings(
                llm_enabled=True,
                llm_base_url="http://127.0.0.1:11434/v1",
                llm_model="qwen2.5:7b",
            )
        )
        is True
    )
