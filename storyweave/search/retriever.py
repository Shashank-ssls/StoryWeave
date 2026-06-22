"""Fenced RAG retrieval + an offline extractive answer (Phase 4).

Pipeline: query -> embed -> fenced ANN search (via ``query/fence.py``) -> ranked
chunks with provenance -> a cited, extractive answer. The answer step needs NO LLM
(rule #4): it selects the most query-relevant sentences from the top revealed chunks
and attaches chapter-cited provenance. An LLM compose step is an opt-in enhancement
for Phase 7. The index is rebuilt from SQLite, the source of truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from storyweave.db.repository import Repository
from storyweave.query import fence
from storyweave.search.embedder import EmbedderProtocol
from storyweave.search.store import BaseVectorStore, SearchHit, StoredChunk

_WORD = re.compile(r"[a-z0-9]+")
_SENT = re.compile(r"[^.!?]+[.!?]?")


def index_work(
    work_id: int,
    repo: Repository,
    store: BaseVectorStore,
    embedder: EmbedderProtocol,
) -> int:
    """Embed every chunk of a work and (re)build its vectors. Idempotent per work."""
    store.reset(work_id)
    chunks = repo.list_chunks_for_work(work_id)
    if not chunks:
        return 0
    ordinal_by_chapter = {c.id: c.ordinal for c in repo.list_chapters(work_id)}
    embeddings = embedder.embed([c.text for c in chunks])
    items = [
        StoredChunk(
            chunk_id=c.id if c.id is not None else -1,
            work_id=work_id,
            chapter_ordinal=ordinal_by_chapter[c.chapter_id],
            char_start=c.char_start,
            char_end=c.char_end,
            text=c.text,
            embedding=emb,
        )
        for c, emb in zip(chunks, embeddings, strict=True)
    ]
    store.add(items)
    return len(items)


def search(
    query: str,
    work_id: int,
    chapter: int,
    store: BaseVectorStore,
    embedder: EmbedderProtocol,
    top_k: int = 5,
) -> list[SearchHit]:
    """Fenced top-k retrieval for a query at reading position N."""
    query_vec = embedder.embed_one(query)
    return fence.visible_chunk_hits(store, query_vec, work_id, chapter, top_k)


@dataclass
class Citation:
    chunk_id: int
    chapter_ordinal: int
    char_start: int
    char_end: int


@dataclass
class Answer:
    text: str
    citations: list[Citation]
    hits: list[SearchHit]


def _keywords(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 2}


def _best_sentence(text: str, query_words: set[str]) -> str:
    sentences = [str(s).strip() for s in _SENT.findall(text) if str(s).strip()]
    if not sentences:
        return text.strip()
    return max(sentences, key=lambda s: len(_keywords(s) & query_words))


def compose_answer(query: str, hits: list[SearchHit], max_passages: int = 3) -> Answer:
    """Offline extractive answer: best sentence per top hit, with chapter citations."""
    if not hits:
        return Answer("No revealed passages match that query.", [], [])

    query_words = _keywords(query)
    parts: list[str] = []
    citations: list[Citation] = []
    for hit in hits[:max_passages]:
        sentence = _best_sentence(hit.text, query_words)
        parts.append(f"{sentence} [ch{hit.chapter_ordinal}]")
        citations.append(
            Citation(hit.chunk_id, hit.chapter_ordinal, hit.char_start, hit.char_end)
        )
    return Answer(" ".join(parts), citations, hits)
