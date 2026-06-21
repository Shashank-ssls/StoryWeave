"""Per-work configuration loader (``storyweave.toml``).

CLAUDE.md rule: novel-specific knobs are *data, never code* — there is no
``if work == "...":`` anywhere. Cleaning regexes, chapter-detection mode, and
chunk sizing all live in an optional per-work TOML file. When the file is absent,
every knob falls back to a sensible default, so any plain ``.txt`` ingests with
zero configuration.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class CleaningConfig(BaseModel):
    # Join words split across a soft line-wrap: "exam-\nple" -> "example".
    dehyphenate: bool = True
    # If True, every single newline is a paragraph break (one-paragraph-per-line
    # sources). If False (default), paragraphs are separated by blank lines and
    # intra-paragraph soft-wraps are collapsed to spaces.
    single_newline_is_paragraph: bool = False
    # Lines fully matching any of these regexes are stripped as cruft (translator
    # notes, nav links, ads). Matches are LOGGED in the ingest report, not dropped
    # silently. Applied case-insensitively to each stripped line.
    cruft_patterns: list[str] = Field(default_factory=list)


class SplittingConfig(BaseModel):
    # "auto": dir -> one file per chapter; single file -> try headings, else whole
    # file as one chapter. The other modes force a strategy.
    chapter_mode: Literal["auto", "file", "heading", "delimiter"] = "auto"
    heading_regex: str = r"^\s*chapter\s+\d+\b.*$"
    delimiter: str = "\n---\n"
    first_chapter_number: int = 1


class ChunkingConfig(BaseModel):
    # Max characters per chunk; a single oversize sentence still becomes one chunk.
    max_chars: int = 1500
    # Sentences of overlap between consecutive chunks (retrieval recall).
    overlap_sentences: int = 1


class WorkConfig(BaseModel):
    title: str | None = None
    slug: str | None = None
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    splitting: SplittingConfig = Field(default_factory=SplittingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)


def load_work_config(path: Path | str | None) -> WorkConfig:
    """Load a ``storyweave.toml`` into a validated :class:`WorkConfig`.

    ``None`` or a missing file yields all-default config.
    """
    if path is None:
        return WorkConfig()
    p = Path(path)
    if not p.exists():
        return WorkConfig()
    with p.open("rb") as fh:
        data = tomllib.load(fh)
    return WorkConfig.model_validate(data)


def find_work_config(source: Path) -> Path | None:
    """Look for a ``storyweave.toml`` beside a source file or inside a source dir."""
    candidate = (source / "storyweave.toml") if source.is_dir() else (
        source.parent / "storyweave.toml"
    )
    return candidate if candidate.exists() else None
