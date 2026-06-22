"""FastAPI dependency providers.

These are the seams the API layer is wired through. The default providers build the
real Repository / Embedder / vector store, but the Embedder and ChromaVectorStore
only load their heavy ML deps lazily (on first use) — so importing and even
constructing them here pulls NO ML into the light venv. Tests override
``get_embedder`` / ``get_vector_store`` with a fake embedder + in-memory store, so
every route is exercisable under ``.venv`` with no ``.venv-ml`` present.
"""

from __future__ import annotations

from collections.abc import Iterator

from storyweave.config import get_settings
from storyweave.db.repository import Repository
from storyweave.search.embedder import Embedder, EmbedderProtocol
from storyweave.search.store import BaseVectorStore, ChromaVectorStore


def get_repository() -> Iterator[Repository]:
    repo = Repository(get_settings().db_path)
    repo.initialize_schema()
    try:
        yield repo
    finally:
        repo.close()


def get_embedder() -> EmbedderProtocol:
    return Embedder()


def get_vector_store() -> BaseVectorStore:
    return ChromaVectorStore(get_settings().vector_dir)
