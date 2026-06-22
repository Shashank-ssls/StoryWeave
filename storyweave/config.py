"""Application configuration.

Settings are loaded from environment variables (prefix ``STORYWEAVE_``) and an
optional ``.env`` file. Rule #5: the LLM enhancement path is OFF by default —
with it off there are zero runtime outbound network calls.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Model weights cache lives on the PROJECT drive (F:), never on C: (env discipline,
# CLAUDE.md §3). Default is repo-root/.hf-cache; override with STORYWEAVE_HF_HOME.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_HF_HOME = _REPO_ROOT / ".hf-cache"


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

    # --- ML / models (off the C: drive) ---
    hf_home: Path = _DEFAULT_HF_HOME
    # Windows needs Developer Mode/admin for symlinks; copying avoids WinError 1314.
    hf_disable_symlinks: bool = True
    gliner_model: str = "urchade/gliner_small-v2.1"
    gliner_threshold: float = 0.4
    gliner_device: str = "cpu"  # "cuda" to use the GPU (4 GB VRAM fits the small model)

    # --- Tier-2 relation extraction (Phase 7a): GLiNER-RelEx, CPU, no VRAM risk. ---
    # It is a GLiNER model, so it honours the same F: cache discipline as gliner_model.
    # This is ENHANCEMENT, never a dependency (rule #4): absent it, the graph degrades
    # cleanly to the Phase 3/5 Tier-1 floor.
    relex_model: str = "knowledgator/gliner-relex-base-v1.0"
    relex_device: str = "cpu"
    relex_ner_threshold: float = 0.3  # entity span recall (model card: 0.3–0.5)
    relex_rel_threshold: float = 0.5  # relation confidence (model card: 0.5+)

    # --- Vector search (Phase 4) ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, CPU-fine
    embedding_device: str = "cpu"
    vector_dir: Path = _REPO_ROOT / ".chroma"  # on-disk Chroma store (gitignored)

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
