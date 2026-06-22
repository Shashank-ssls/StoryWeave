"""Phase 4: vector store + fenced RAG retrieval.

Pure-Python tests use a deterministic FakeEmbedder + InMemoryVectorStore so the fence
and retrieval logic run in the light venv. Real embedding (sentence-transformers) and
the Chroma backend are importorskip-gated for .venv-ml.
"""

from __future__ import annotations

import hashlib

import pytest

from storyweave.db.models import Chapter, Chunk, Work
from storyweave.db.repository import Repository
from storyweave.search.retriever import compose_answer, index_work, search
from storyweave.search.store import InMemoryVectorStore, SearchHit, StoredChunk

_DIM = 64


class FakeEmbedder:
    """Deterministic hashing bag-of-words embedder (no ML). Shared, fixed dimension."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self._vec(text)

    @staticmethod
    def _vec(text: str) -> list[float]:
        v = [0.0] * _DIM
        for word in text.lower().split():
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % _DIM
            v[idx] += 1.0
        return v


def _hit(chunk_id: int, chapter: int, text: str = "x") -> SearchHit:
    return SearchHit(chunk_id, 1, chapter, 0, len(text), text, 0.9)


# --- store ----------------------------------------------------------------- #


def test_inmemory_store_fences_and_isolates_by_work() -> None:
    store = InMemoryVectorStore()
    emb = FakeEmbedder()
    store.add(
        [
            StoredChunk(1, work_id=1, chapter_ordinal=1, char_start=0, char_end=3, text="ring",
                        embedding=emb.embed_one("ring")),
            StoredChunk(2, work_id=1, chapter_ordinal=5, char_start=0, char_end=4, text="crown",
                        embedding=emb.embed_one("crown")),
            StoredChunk(3, work_id=2, chapter_ordinal=1, char_start=0, char_end=4, text="other",
                        embedding=emb.embed_one("other")),
        ]
    )
    # Fence: at N=3 the ch5 chunk is ineligible.
    hits = store.query(emb.embed_one("crown ring"), work_id=1, top_k=10, max_chapter=3)
    assert {h.chunk_id for h in hits} == {1}
    # Work isolation: work 2's chunk never leaks into work 1 results.
    assert all(h.work_id == 1 for h in hits)


# --- retrieval (MANDATORY fence regression) -------------------------------- #


def _seed_work(repo: Repository) -> int:
    wid = repo.create_work(Work(slug="t", title="T"))
    for ordinal in range(1, 6):
        text = f"Secret passage number {ordinal} mentions topic{ordinal}."
        cid = repo.add_chapter(
            Chapter(work_id=wid, ordinal=ordinal, clean_text=text, content_hash=f"h{ordinal}")
        )
        repo.add_chunk(
            Chunk(chapter_id=cid, work_id=wid, ordinal=0, char_start=0,
                  char_end=len(text), text=text, content_hash=f"c{ordinal}")
        )
    return wid


def test_search_excludes_later_chapter_chunk() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _seed_work(repo)
        store = InMemoryVectorStore()
        embedder = FakeEmbedder()
        assert index_work(wid, repo, store, embedder) == 5

        # Query for the ch5 passage's exact text, but read only up to ch3.
        hits = search("topic5 Secret passage number 5", wid, chapter=3,
                      store=store, embedder=embedder, top_k=10)
        assert hits, "expected some revealed results"
        assert all(h.chapter_ordinal <= 3 for h in hits)
        assert all(h.chapter_ordinal != 5 for h in hits)  # the ch5 chunk is fenced out

        # At N=5 the same query can reach it.
        later = search("topic5 Secret passage number 5", wid, chapter=5,
                       store=store, embedder=embedder, top_k=10)
        assert any(h.chapter_ordinal == 5 for h in later)


def test_index_work_is_idempotent() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _seed_work(repo)
        store = InMemoryVectorStore()
        embedder = FakeEmbedder()
        index_work(wid, repo, store, embedder)
        index_work(wid, repo, store, embedder)
        assert store.count(wid) == 5  # rebuilt, not duplicated


# --- extractive answer ----------------------------------------------------- #


def test_compose_answer_cites_chapters() -> None:
    hits = [
        _hit(1, 2, "Wren stole the heron ring. He fled the market."),
        _hit(2, 1, "Aldercross was cold."),
    ]
    answer = compose_answer("who stole the ring", hits)
    assert "[ch2]" in answer.text
    assert answer.citations[0].chapter_ordinal == 2
    assert len(answer.citations) == 2


def test_compose_answer_handles_no_hits() -> None:
    answer = compose_answer("anything", [])
    assert answer.citations == []
    assert "No revealed passages" in answer.text


# --- ML-gated: real embeddings + Chroma ------------------------------------ #


def test_real_embedder_dimension_and_similarity() -> None:
    pytest.importorskip("sentence_transformers")
    from storyweave.search.embedder import Embedder

    emb = Embedder()
    vecs = emb.embed(["the king wore a crown", "the monarch's crown", "a fish swims"])
    assert len({len(v) for v in vecs}) == 1  # uniform dimension

    from storyweave.search.store import _cosine

    assert _cosine(vecs[0], vecs[1]) > _cosine(vecs[0], vecs[2])  # related > unrelated


def test_chroma_round_trip_is_fenced() -> None:
    pytest.importorskip("chromadb")
    import tempfile

    from storyweave.search.store import ChromaVectorStore

    emb = FakeEmbedder()
    # ignore_cleanup_errors: on Windows Chroma keeps chroma.sqlite3 open, which would
    # otherwise make the tempdir teardown raise PermissionError after the test passes.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        store = ChromaVectorStore(tmp, collection_name="chunks_test")
        store.add(
            [
                StoredChunk(1, 1, 1, 0, 4, "ring", emb.embed_one("ring")),
                StoredChunk(2, 1, 5, 0, 5, "crown", emb.embed_one("crown")),
            ]
        )
        hits = store.query(emb.embed_one("crown"), work_id=1, top_k=10, max_chapter=3)
        assert {h.chunk_id for h in hits} == {1}  # ch5 fenced out at N=3
        assert store.count(1) == 2
