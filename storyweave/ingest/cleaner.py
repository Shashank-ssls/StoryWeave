"""Stage 0 text cleaning: the canonical offset space everything downstream indexes into.

Cleaning is deterministic and paragraph-preserving so that chunk offsets are stable.
Cruft is *logged*, never silently dropped — the caller gets back every removed line and
every watermark hit for the ingest report.

Order matters, and it is the order below (retrofit R2):

1. **NFKC** — collapses full-width forms, ligatures and compatibility variants.
2. **Homoglyph folding** — Greek/Cyrillic look-alikes to Latin. Must run BEFORE the
   watermark patterns, because the watermarks are obfuscated with exactly these
   characters (``ndαsnοvεl.cοm``); after folding, one plain regex catches every spelling.
3. **Watermark removal** — configured wrapper tags first, then domain-like tokens.
4. **Quote straightening** — curly to straight, *preserving kind*.
5. **Whitespace / paragraph normalisation** — defines the canonical coordinate space.

De-hyphenation and line-level cruft stripping sit between 3 and 5, both pre-existing.

The raw text is stored untouched (``chapters.clean_text`` is the cleaned copy; the
source file is never rewritten), so nothing here is irreversible.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from storyweave.ingest.homoglyphs import count_folded, fold_homoglyphs
from storyweave.ingest.work_config import CleaningConfig

# Soft line-wrap hyphen: a word char, a hyphen, a newline, then a word char.
_DEHYPHEN = re.compile(r"(?<=\w)-\n(?=\w)")
# Collapse runs of spaces/tabs (not newlines) to a single space.
_SPACES = re.compile(r"[ \t]+")
# Three or more newlines collapse to a paragraph break (two newlines).
_MANY_NEWLINES = re.compile(r"\n{3,}")

# Curly -> straight, KIND PRESERVED. Doubles become '"', singles become "'"; a single
# quote is never promoted to a double one. U+2018/2019 also serve as apostrophes
# ("don't"), which is the other reason the kinds must not be merged. Brackets are
# absent from this table on purpose: "[Can you hear me?]" is a system message in this
# corpus and its brackets are content.
_QUOTES: dict[str, str] = {
    "“": '"',  # “ LEFT DOUBLE QUOTATION MARK
    "”": '"',  # ” RIGHT DOUBLE QUOTATION MARK
    "„": '"',  # „ DOUBLE LOW-9
    "‟": '"',  # ‟ DOUBLE HIGH-REVERSED-9
    "″": '"',  # ″ DOUBLE PRIME
    "«": '"',  # « LEFT-POINTING DOUBLE ANGLE
    "»": '"',  # » RIGHT-POINTING DOUBLE ANGLE
    "‘": "'",  # ‘ LEFT SINGLE QUOTATION MARK
    "’": "'",  # ’ RIGHT SINGLE QUOTATION MARK (also the apostrophe)
    "‚": "'",  # ‚ SINGLE LOW-9
    "‛": "'",  # ‛ SINGLE HIGH-REVERSED-9
    "′": "'",  # ′ PRIME
}
_QUOTE_TRANSLATION = str.maketrans(_QUOTES)


@dataclass
class CleanResult:
    text: str
    removed_lines: list[str] = field(default_factory=list)
    #: Watermark tag names whose markup was stripped -> how many tags were removed.
    watermark_tags_removed: Counter[str] = field(default_factory=Counter)
    #: Domain-like watermark tokens removed -> how many times each appeared.
    watermark_tokens_removed: Counter[str] = field(default_factory=Counter)
    #: Homoglyph code points folded to Latin -> how many of each.
    homoglyphs_folded: Counter[str] = field(default_factory=Counter)

    @property
    def watermark_hits(self) -> int:
        """Total watermark removals: every tag stripped plus every token removed."""
        return sum(self.watermark_tags_removed.values()) + sum(
            self.watermark_tokens_removed.values()
        )


def strip_watermark_tags(text: str, tags: list[str]) -> tuple[str, Counter[str]]:
    """Remove ``<tag>``/``</tag>`` markup for each configured tag, KEEPING inner text.

    The inner text is story prose — that is the whole point of this watermark style, and
    deleting the block would delete part of the chapter. Only the markup goes.
    """
    hits: Counter[str] = Counter()
    for tag in tags:
        pattern = re.compile(rf"</?\s*{re.escape(tag)}\s*/?>", re.IGNORECASE)
        text, n = pattern.subn("", text)
        if n:
            hits[tag] = n
    return text, hits


def strip_watermark_tokens(text: str, patterns: list[str]) -> tuple[str, Counter[str]]:
    """Remove domain-like watermark tokens. Run this AFTER homoglyph folding."""
    hits: Counter[str] = Counter()
    for raw in patterns:
        compiled = re.compile(raw, re.IGNORECASE)
        # finditer + group(0), so a pattern with capture groups still reports the text
        # that was actually deleted rather than one of its groups.
        for m in compiled.finditer(text):
            hits[m.group(0)] += 1
        text = compiled.sub("", text)
    return text, hits


def straighten_quotes(text: str) -> str:
    """Curly quotes to straight ones, preserving double-vs-single. Brackets untouched."""
    return text.translate(_QUOTE_TRANSLATION)


def clean_text(raw: str, config: CleaningConfig | None = None) -> CleanResult:
    """Clean ``raw`` into canonical text, returning the text + everything removed."""
    cfg = config or CleaningConfig()

    # 1. Unicode normalization (collapses full-width punctuation, ligatures, etc.).
    text = unicodedata.normalize("NFKC", raw)

    # 2. Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Homoglyph folding — BEFORE the watermark patterns, so they see Latin text.
    folded: Counter[str] = Counter()
    if cfg.fold_homoglyphs:
        folded = count_folded(text)
        text = fold_homoglyphs(text)

    # 4. Watermark removal: wrapper tags, then domain-like tokens.
    text, tag_hits = strip_watermark_tags(text, cfg.watermark_tags)
    text, token_hits = strip_watermark_tokens(text, cfg.watermark_token_patterns)

    # 5. Quote straightening, kind preserved.
    if cfg.straighten_quotes:
        text = straighten_quotes(text)

    # 6. De-hyphenate soft line-wraps before any line-based processing.
    if cfg.dehyphenate:
        text = _DEHYPHEN.sub("", text)

    # 7. Strip cruft lines (logged), line by line.
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

    # 8. Re-flow into clean paragraphs (this defines the canonical offset space).
    text = _reflow_paragraphs(text, cfg.single_newline_is_paragraph)

    return CleanResult(
        text=text,
        removed_lines=removed,
        watermark_tags_removed=tag_hits,
        watermark_tokens_removed=token_hits,
        homoglyphs_folded=folded,
    )


def _reflow_paragraphs(text: str, single_newline_is_paragraph: bool) -> str:
    """Produce canonical text: paragraphs joined by exactly one blank line.

    Within a paragraph, soft line-wraps become single spaces. This is the stable
    coordinate space that chunk char offsets index into.
    """
    if single_newline_is_paragraph:
        # Every non-empty line is its own paragraph.
        raw_paragraphs = list(text.split("\n"))
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
