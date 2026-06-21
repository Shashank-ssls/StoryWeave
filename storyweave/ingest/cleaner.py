"""Text cleaning: NFKC, de-hyphenation, config-driven cruft stripping, paragraphs.

Cleaning is deterministic and paragraph-preserving so that downstream chunk
offsets are stable. Cruft is *logged*, never silently dropped — the caller gets
back every removed line for the ingest report.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from storyweave.ingest.work_config import CleaningConfig

# Soft line-wrap hyphen: a word char, a hyphen, a newline, then a word char.
_DEHYPHEN = re.compile(r"(?<=\w)-\n(?=\w)")
# Collapse runs of spaces/tabs (not newlines) to a single space.
_SPACES = re.compile(r"[ \t]+")
# Three or more newlines collapse to a paragraph break (two newlines).
_MANY_NEWLINES = re.compile(r"\n{3,}")


@dataclass
class CleanResult:
    text: str
    removed_lines: list[str] = field(default_factory=list)


def clean_text(raw: str, config: CleaningConfig | None = None) -> CleanResult:
    """Clean ``raw`` into canonical text, returning the text + removed cruft lines."""
    cfg = config or CleaningConfig()

    # 1. Unicode normalization (collapses full-width punctuation, ligatures, etc.).
    text = unicodedata.normalize("NFKC", raw)

    # 2. Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. De-hyphenate soft line-wraps before any line-based processing.
    if cfg.dehyphenate:
        text = _DEHYPHEN.sub("", text)

    # 4. Strip cruft lines (logged), line by line.
    removed: list[str] = []
    if cfg.cruft_patterns:
        patterns = [re.compile(p, re.IGNORECASE) for p in cfg.cruft_patterns]
        kept: list[str] = []
        for line in text.split("\n"):
            if line.strip() and any(p.search(line) for p in patterns):
                removed.append(line.strip())
            else:
                kept.append(line)
        text = "\n".join(kept)

    # 5. Re-flow into clean paragraphs (this defines the canonical offset space).
    text = _reflow_paragraphs(text, cfg.single_newline_is_paragraph)

    return CleanResult(text=text, removed_lines=removed)


def _reflow_paragraphs(text: str, single_newline_is_paragraph: bool) -> str:
    """Produce canonical text: paragraphs joined by exactly one blank line.

    Within a paragraph, soft line-wraps become single spaces. This is the stable
    coordinate space that chunk char offsets index into.
    """
    if single_newline_is_paragraph:
        # Every non-empty line is its own paragraph.
        raw_paragraphs = [ln for ln in text.split("\n")]
    else:
        # Blank line(s) separate paragraphs; soft newlines are intra-paragraph.
        text = _MANY_NEWLINES.sub("\n\n", text)
        raw_paragraphs = text.split("\n\n")

    paragraphs: list[str] = []
    for para in raw_paragraphs:
        # Collapse internal newlines + redundant spaces to single spaces.
        collapsed = _SPACES.sub(" ", para.replace("\n", " ")).strip()
        if collapsed:
            paragraphs.append(collapsed)

    return "\n\n".join(paragraphs)
