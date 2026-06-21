"""Phase 1: chapter detection, sentence spans, chunking, and the offset invariant."""

from __future__ import annotations

from pathlib import Path

from storyweave.ingest.splitter import (
    chunk_chapter,
    chunk_spans,
    detect_chapters,
    sentence_spans,
)
from storyweave.ingest.work_config import ChunkingConfig, SplittingConfig


def test_sentence_spans_slice_exactly() -> None:
    text = "Hello world. Second one! Third?"
    spans = sentence_spans(text)
    assert len(spans) == 3
    assert text[spans[0][0] : spans[0][1]] == "Hello world."
    assert text[spans[2][0] : spans[2][1]] == "Third?"


def test_chunk_spans_respect_max_chars() -> None:
    spans = [(0, 10), (10, 20), (20, 30)]
    chunks = chunk_spans(spans, max_chars=20, overlap_sentences=0)
    # First two sentences fit in 20 chars; third starts a new chunk.
    assert chunks[0] == (0, 20)
    assert chunks[-1][1] == 30


def test_oversize_sentence_becomes_its_own_chunk() -> None:
    spans = [(0, 100)]
    chunks = chunk_spans(spans, max_chars=20)
    assert chunks == [(0, 100)]


def test_chunk_chapter_offset_invariant() -> None:
    clean = (
        "The thief moved quietly. He took the ring and ran. "
        "Nobody saw his face that night. The watch arrived too late."
    )
    chunks = chunk_chapter(clean, ChunkingConfig(max_chars=50, overlap_sentences=1))
    assert chunks
    for ch in chunks:
        assert clean[ch.char_start : ch.char_end] == ch.text


def test_detect_chapters_heading_mode() -> None:
    text = "Chapter 1: Alpha\nbody a\nChapter 2: Beta\nbody b"
    chapters = detect_chapters(
        _tmp_file(text), SplittingConfig(chapter_mode="heading")
    )
    assert [c.ordinal for c in chapters] == [1, 2]
    assert chapters[0].title is not None and "Alpha" in chapters[0].title
    assert "body a" in chapters[0].raw_text


def test_detect_chapters_delimiter_mode() -> None:
    text = "first part\n---\nsecond part"
    chapters = detect_chapters(
        _tmp_file(text), SplittingConfig(chapter_mode="delimiter")
    )
    assert len(chapters) == 2


# --- helper ---------------------------------------------------------------- #

import tempfile  # noqa: E402


def _tmp_file(text: str) -> Path:
    fd = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    fd.write(text)
    fd.close()
    return Path(fd.name)
