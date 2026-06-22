"""Chunk embedding via sentence-transformers (lazy import, .venv-ml).

Embeddings are L2-normalized so cosine similarity reduces to a dot product, matching
the Chroma cosine space and the in-memory store. Like GLiNER, the heavy import is
lazy and the model cache is forced onto F: before the first HuggingFace import.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from storyweave.config import Settings, get_settings
from storyweave.nlp.extractor import configure_hf_cache

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sentence_transformers import SentenceTransformer


@runtime_checkable
class EmbedderProtocol(Protocol):
    """Minimal embedding interface (real or fake), so retrieval is testable sans ML."""

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_one(self, text: str) -> list[float]: ...


class Embedder:
    """sentence-transformers wrapper. Batchable; lazy model load."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self.model_name = model_name or self._settings.embedding_model
        self.device = device or self._settings.embedding_device
        self._model: SentenceTransformer | None = None

    def _ensure_loaded(self) -> SentenceTransformer:
        if self._model is None:
            configure_hf_cache(self._settings)
            from sentence_transformers import SentenceTransformer  # lazy heavy import

            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_loaded()
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
