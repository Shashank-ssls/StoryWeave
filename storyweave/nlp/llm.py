"""Optional LLM enhancement client — the Phase-7b wired path (OFF by default).

Rules #4 and #5 are enforced *structurally* here, not by convention:

* ``llm_available`` is the single gate every caller must pass. With
  ``llm_enabled=False`` (the default) it returns ``False`` and **no client is ever
  constructed and no socket is ever opened** — zero runtime outbound calls.
* :class:`LlmClient` refuses to construct while disabled (raises), so a future caller
  cannot accidentally bypass the flag.

This module wires the path proven by the go/no-go gate (``eval/llm_gate.py``); it does
NOT implement Tier-2 or Tier-3 extraction — that is Phase 7c. It speaks the
OpenAI-compatible Chat Completions API (``{base_url}/chat/completions``) so it is
runner-agnostic: local Ollama today, any compatible endpoint later. Stdlib only
(``urllib``) — no new dependency, imports cleanly in the light ``.venv``.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from storyweave.config import Settings, get_settings


def llm_available(settings: Settings | None = None) -> bool:
    """True only when the LLM layer is explicitly enabled AND fully configured.

    The mandatory gate for every caller. False by default → callers fall back to the
    GLiNER/relex floor and make no outbound calls (graceful degradation, rule #4).
    """
    cfg = settings or get_settings()
    return bool(cfg.llm_enabled and cfg.llm_base_url and cfg.llm_model)


class LlmClient:
    """Thin OpenAI-compatible chat client. Constructible only when the flag is ON."""

    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        if not cfg.llm_enabled:
            # Hard guard: the disabled path must never reach the network.
            raise RuntimeError(
                "LLM is disabled (llm_enabled=False); refusing to construct a client"
            )
        if not (cfg.llm_base_url and cfg.llm_model):
            raise RuntimeError("LLM enabled but llm_base_url/llm_model are not configured")
        self.base_url = cfg.llm_base_url.rstrip("/")
        self.model = cfg.llm_model
        self.api_key = cfg.llm_api_key
        self.temperature = cfg.llm_temperature

    def complete_json(self, system: str, user: str, timeout: float = 900.0) -> dict[str, Any]:
        """Return the model's strict-JSON object reply (response_format = json_object).

        Used by Phase 7c for identity/relation inference; provided here so the wired
        path is testable end to end. Never called while ``llm_enabled=False``.
        """
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed: dict[str, Any] = json.loads(content)
        return parsed
