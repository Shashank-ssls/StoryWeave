"""Vector store adapters — local, on-disk, no cloud (rule #5).

One interface (:class:`BaseVectorStore`), two backends:

* :class:`InMemoryVectorStore` — pure-Python brute-force cosine. No heavy deps, so it
  runs in the light venv and backs the fence/retriever unit tests with a fake embedder.
* :class:`ChromaVectorStore` — persistent on-disk Chroma (lazy import, ``.venv-ml``).

Every vector carries ``work_id`` + ``chapter_ordinal`` (the reveal key) as metadata,
so the index is reveal-aware from the start and the fence can be applied AT THE INDEX
(in the ``query`` call), never after results return to the caller. The index is fully
rebuildable from SQLite — it stores nothing that isn't derived from chunks.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class StoredChunk:
    chunk_id: int
    work_id: int
    chapter_ordinal: int  # the reveal key: a chunk is visible once the reader reaches it
    char_start: int
    char_end: int
    text: str
    embedding: list[float]


@dataclass
class SearchHit:
    chunk_id: int
    work_id: int
    chapter_ordinal: int
    char_start: int
    char_end: int
    text: str
    score: float


class BaseVectorStore(ABC):
    @abstractmethod
    def add(self, items: list[StoredChunk]) -> None: ...

    @abstractmethod
    def query(
        self, embedding: list[float], work_id: int, top_k: int, max_chapter: int
    ) -> list[SearchHit]:
        """ANN search restricted to ``work_id`` AND ``chapter_ordinal <= max_chapter``.

        The reveal filter is applied HERE, at the index level, before results are
        returned — there is no unfenced path out of the store.
        """

    @abstractmethod
    def reset(self, work_id: int) -> None: ...

    @abstractmethod
    def count(self, work_id: int) -> int: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryVectorStore(BaseVectorStore):
    """Brute-force cosine store. Exact, dependency-free; ideal for tests + small works."""

    def __init__(self) -> None:
        self._items: dict[int, StoredChunk] = {}

    def add(self, items: list[StoredChunk]) -> None:
        for it in items:
            self._items[it.chunk_id] = it

    def query(
        self, embedding: list[float], work_id: int, top_k: int, max_chapter: int
    ) -> list[SearchHit]:
        # Fence FIRST: only revealed chunks of this work are eligible.
        eligible = [
            it
            for it in self._items.values()
            if it.work_id == work_id and it.chapter_ordinal <= max_chapter
        ]
        scored = sorted(
            ((_cosine(embedding, it.embedding), it) for it in eligible),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [
            SearchHit(
                chunk_id=it.chunk_id,
                work_id=it.work_id,
                chapter_ordinal=it.chapter_ordinal,
                char_start=it.char_start,
                char_end=it.char_end,
                text=it.text,
                score=score,
            )
            for score, it in scored[:top_k]
        ]

    def reset(self, work_id: int) -> None:
        self._items = {k: v for k, v in self._items.items() if v.work_id != work_id}

    def count(self, work_id: int) -> int:
        return sum(1 for it in self._items.values() if it.work_id == work_id)


class ChromaVectorStore(BaseVectorStore):
    """Persistent on-disk Chroma backend (lazy import; runs under .venv-ml)."""

    def __init__(self, path: Path | str, collection_name: str = "chunks") -> None:
        self._path = str(path)
        self._collection_name = collection_name
        self._collection: Any = None

    def _coll(self) -> Any:
        if self._collection is None:
            Path(self._path).mkdir(parents=True, exist_ok=True)
            import chromadb  # lazy: heavy import only under .venv-ml

            client = chromadb.PersistentClient(path=self._path)
            self._collection = client.get_or_create_collection(
                name=self._collection_name, metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def add(self, items: list[StoredChunk]) -> None:
        if not items:
            return
        coll = self._coll()
        coll.upsert(
            ids=[str(it.chunk_id) for it in items],
            embeddings=[it.embedding for it in items],
            documents=[it.text for it in items],
            metadatas=[
                {
                    "chunk_id": it.chunk_id,
                    "work_id": it.work_id,
                    "chapter_ordinal": it.chapter_ordinal,
                    "char_start": it.char_start,
                    "char_end": it.char_end,
                }
                for it in items
            ],
        )

    def query(
        self, embedding: list[float], work_id: int, top_k: int, max_chapter: int
    ) -> list[SearchHit]:
        coll = self._coll()
        res = coll.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where={
                "$and": [
                    {"work_id": work_id},
                    {"chapter_ordinal": {"$lte": max_chapter}},  # fence at the index
                ]
            },
        )
        hits: list[SearchHit] = []
        metas = res.get("metadatas") or [[]]
        docs = res.get("documents") or [[]]
        dists = res.get("distances") or [[]]
        for meta, doc, dist in zip(metas[0], docs[0], dists[0], strict=False):
            hits.append(
                SearchHit(
                    chunk_id=int(meta["chunk_id"]),
                    work_id=int(meta["work_id"]),
                    chapter_ordinal=int(meta["chapter_ordinal"]),
                    char_start=int(meta["char_start"]),
                    char_end=int(meta["char_end"]),
                    text=doc,
                    score=1.0 - float(dist),  # cosine distance -> similarity
                )
            )
        return hits

    def reset(self, work_id: int) -> None:
        self._coll().delete(where={"work_id": work_id})

    def count(self, work_id: int) -> int:
        got = self._coll().get(where={"work_id": work_id})
        return len(got.get("ids") or [])
