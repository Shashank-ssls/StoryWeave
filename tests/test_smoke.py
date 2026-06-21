"""Phase 0 smoke tests: version is reported and the LLM layer is OFF by default."""

from __future__ import annotations

from typer.testing import CliRunner

from storyweave import __version__
from storyweave.cli.main import app
from storyweave.config import Settings


def test_version_constant_is_set() -> None:
    assert __version__
    assert __version__[0].isdigit()


def test_cli_version_command() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_llm_is_off_by_default(monkeypatch: object) -> None:
    # Rule #5: no STORYWEAVE_* env => LLM disabled, zero outbound calls.
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.llm_enabled is False
    assert settings.llm_api_key is None
