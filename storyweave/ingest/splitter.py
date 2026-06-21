"""Chapter detection + sentence-aligned chunking.

Two jobs:

1. **Chapter detection** — turn a source (a directory of per-chapter ``.txt`` files,
   or a single file split by heading regex / delimiter) into ordered raw chapters.
2. **Chunking** — slice a chapter's *clean* text into sentence-aligned chunks whose
   char offsets index exactly into that clean text.

Hard invariant (guaranteed structurally): every chunk's text is produced by slicing
``clean_text[char_start:char_end]``, so ``clean_text[start:end] == chunk.text`` always
holds, regardless of sentence-splitter quality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from storyweave.ingest.work_config import ChunkingConfig, SplittingConfig

# Sentence terminator: ASCII + common CJK end punctuation (MTL text), optionally
# followed by a closing quote/bracket, then whitespace or end-of-text.
_SENT_END = re.compile(r'[.!?。！？][\"\'”’)\]]?(?=\s|$)')
_LEADING_INT = re.compile(r"\d+")


@dataclass
class RawChapter:
    ordinal: int
    title: str | None
    raw_text: str
    source_path: str | None = None


# --------------------------------------------------------------------------- #
# Chapter detection
# --------------------------------------------------------------------------- #


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _ordinal_from_name(name: str, fallback: int) -> int:
    m = _LEADING_INT.search(name)
    return int(m.group()) if m else fallback


def detect_chapters(source: Path, cfg: SplittingConfig) -> list[RawChapter]:
    """Resolve a source path into ordered raw chapters per the configured mode."""
    if source.is_dir():
        return _chapters_from_dir(source, cfg)

    text = _read(source)
    mode = cfg.chapter_mode
    if mode == "file":
        # A single file treated as exactly one chapter.
        return [RawChapter(cfg.first_chapter_number, None, text, str(source))]
    if mode == "heading":
        return _split_by_heading(text, cfg, str(source))
    if mode == "delimiter":
        return _split_by_delimiter(text, cfg, str(source))

    # auto: prefer headings, then delimiter, else the whole file as one chapter.
    heading = _split_by_heading(text, cfg, str(source))
    if len(heading) >= 1 and _has_heading(text, cfg):
        return heading
    if cfg.delimiter in text:
        return _split_by_delimiter(text, cfg, str(source))
    return [RawChapter(cfg.first_chapter_number, None, text, str(source))]


def _chapters_from_dir(source: Path, cfg: SplittingConfig) -> list[RawChapter]:
    files = sorted(p for p in source.glob("*.txt") if p.is_file())
    chapters: list[RawChapter] = []
    for idx, path in enumerate(files):
        ordinal = _ordinal_from_name(path.stem, cfg.first_chapter_number + idx)
        title, body = _extract_leading_heading(_read(path), cfg, fallback=path.stem)
        chapters.append(RawChapter(ordinal, title, body, str(path)))
    chapters.sort(key=lambda c: c.ordinal)
    return chapters


def _extract_leading_heading(
    text: str, cfg: SplittingConfig, fallback: str
) -> tuple[str, str]:
    """If the first non-empty line is a heading, use it as the title and drop it."""
    heading = re.compile(cfg.heading_regex, re.IGNORECASE)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if heading.match(line):
            return line.strip(), "\n".join(lines[i + 1 :])
        break  # first content line is not a heading
    return fallback, text


def _has_heading(text: str, cfg: SplittingConfig) -> bool:
    return re.search(cfg.heading_regex, text, re.IGNORECASE | re.MULTILINE) is not None


def _split_by_heading(text: str, cfg: SplittingConfig, source: str) -> list[RawChapter]:
    pattern = re.compile(cfg.heading_regex, re.IGNORECASE | re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return [RawChapter(cfg.first_chapter_number, None, text, source)]

    chapters: list[RawChapter] = []
    for i, m in enumerate(matches):
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group().strip()
        ordinal = _ordinal_from_name(title, cfg.first_chapter_number + i)
        chapters.append(RawChapter(ordinal, title, text[body_start:body_end], source))
    return chapters


def _split_by_delimiter(text: str, cfg: SplittingConfig, source: str) -> list[RawChapter]:
    parts = [p for p in text.split(cfg.delimiter) if p.strip()]
    return [
        RawChapter(cfg.first_chapter_number + i, None, part, source)
        for i, part in enumerate(parts)
    ]


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return ordered, non-overlapping (start, end) spans of sentences in ``text``.

    Leading whitespace is excluded from each span; trailing terminator is included.
    Spans never overlap, so they can be grouped into chunks by slicing.
    """
    spans: list[tuple[int, int]] = []
    cursor = 0
    for m in _SENT_END.finditer(text):
        end = m.end()
        start = cursor
        while start < end and text[start].isspace():
            start += 1
        if start < end:
            spans.append((start, end))
        cursor = end
    # Trailing remainder with no terminator.
    start = cursor
    while start < len(text) and text[start].isspace():
        start += 1
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def chunk_spans(
    spans: list[tuple[int, int]], max_chars: int, overlap_sentences: int = 0
) -> list[tuple[int, int]]:
    """Group sentence spans into chunk spans no longer than ``max_chars``.

    A single sentence longer than ``max_chars`` becomes its own (oversize) chunk.
    """
    if not spans:
        return []
    chunks: list[tuple[int, int]] = []
    i = 0
    n = len(spans)
    while i < n:
        first = i
        chunk_start = spans[i][0]
        chunk_end = spans[i][1]
        i += 1
        while i < n and spans[i][1] - chunk_start <= max_chars:
            chunk_end = spans[i][1]
            i += 1
        chunks.append((chunk_start, chunk_end))
        if overlap_sentences > 0 and i < n:
            i = max(first + 1, i - overlap_sentences)
    return chunks


@dataclass
class ChunkSpan:
    ordinal: int
    char_start: int
    char_end: int
    text: str


def chunk_chapter(clean_text: str, cfg: ChunkingConfig) -> list[ChunkSpan]:
    """Chunk a chapter's clean text. Slicing guarantees the offset invariant."""
    spans = chunk_spans(
        sentence_spans(clean_text), cfg.max_chars, cfg.overlap_sentences
    )
    return [
        ChunkSpan(ordinal=idx, char_start=s, char_end=e, text=clean_text[s:e])
        for idx, (s, e) in enumerate(spans)
    ]
