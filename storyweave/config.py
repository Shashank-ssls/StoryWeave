"""Application configuration.

Settings are loaded from environment variables (prefix ``STORYWEAVE_``) and an
optional ``.env`` file. Rule #5: the LLM enhancement path is OFF by default —
with it off there are zero runtime outbound network calls.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All knobs are overridable via ``STORYWEAVE_*`` env vars."""

    model_config = SettingsConfigDict(
        env_prefix="STORYWEAVE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Local-first storage (rule #5): everything lives on local disk. ---
    data_dir: Path = Path("data")
    db_path: Path = Path("data/storyweave.sqlite")

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # --- LLM enhancement layer (rule #4 + #5): OFF by default. ---
    # When False, the pipeline runs the GLiNER floor only and makes no outbound calls.
    llm_enabled: bool = False
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
