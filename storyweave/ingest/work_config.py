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


class ExtractionConfig(BaseModel):
    # Override the global GLiNER model/threshold per work if needed (knobs are data).
    model: str | None = None
    threshold: float | None = None
    device: str | None = None
    # Optional per-work extra label prompts mapped to a canonical 8-type name, e.g.
    # {"power system": "Concept"}. Helps recall for genre-specific common nouns.
    extra_labels: dict[str, str] = Field(default_factory=dict)


class RelationConfig(BaseModel):
    # --- Tier-1 structural (Phase 3): co-occurrence rules, zero ML. ---
    # Two entities co-occurring within this many characters (gap between their
    # mention spans, same chapter) become a candidate Tier-1 edge.
    window_chars: int = 250
    # Minimum number of co-occurrences before an edge is kept (noise floor).
    min_cooccurrences: int = 1

    # --- Tier-2 social (Phase 7a): GLiNER-RelEx overrides (knobs are data). ---
    # None -> fall back to the global Settings.relex_* values.
    relex_model: str | None = None
    relex_ner_threshold: float | None = None
    relex_rel_threshold: float | None = None


class IdentityConfig(BaseModel):
    # --- Tier-3 identity inference (Phase 7c): LLM-inferred, citation-gated. ---
    # Identity is about persons, so candidate pairs are drawn from these node types.
    candidate_types: list[str] = Field(default_factory=lambda: ["Character", "Title"])
    # Cap on how many co-occurring pairs we ask the LLM about (real novels have many);
    # most-important pairs first. Knob is DATA (per-work), never hardcoded.
    max_candidate_pairs: int = 60


class CorefConfig(BaseModel):
    # --- Conservative coreference merge (entity-level Tier-1/2 cleanup). ---
    # Fold first/second-person self-reference pronoun NODES (`I`, `you`, ...) into the
    # single POV character so split edges consolidate. OFF by default: only enable for a
    # range that is UNAMBIGUOUSLY single-POV (over-merge is worse than the junk). This is
    # NOT identity inference (Tier-3) — it is string-level coref the Phase-2 clusterer
    # cannot do (a pronoun shares no surface tokens with the name it refers to).
    merge_self_reference: bool = False
    # Explicit POV canonical name (matched by normalized surface). Empty -> auto-detect
    # the single most-important Character; a tie at the top SKIPS the merge (unsure).
    # Per-work DATA, never hardcoded in code (no `if work == "Sunny"`).
    pov_character: str = ""
    # The self-reference surface set (DATA, overridable per work). English first/second
    # person singular — these denote the narrator/addressee, i.e. the POV character, in a
    # single-POV range. Ambiguous group pronouns (we/they) are deliberately excluded.
    self_reference_surfaces: list[str] = Field(
        default_factory=lambda: [
            "I", "me", "my", "mine", "myself",
            "you", "your", "yours", "yourself",
        ]
    )


class WorkConfig(BaseModel):
    title: str | None = None
    slug: str | None = None
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    splitting: SplittingConfig = Field(default_factory=SplittingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    relations: RelationConfig = Field(default_factory=RelationConfig)
    identity: IdentityConfig = Field(default_factory=IdentityConfig)
    coref: CorefConfig = Field(default_factory=CorefConfig)


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
