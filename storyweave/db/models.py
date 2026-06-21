"""Pydantic mirrors of the persisted schema + the full 8-type ontology vocabulary.

This module is the single Python-side definition of the ontology (SPEC §5):
the eight node types, the per-type subtype hints, and the three-tier relationship
vocabulary. The SQL schema in :mod:`storyweave.db.repository` enforces the same
node-type and tier constraints; these mirrors keep the application layer honest.

Nothing here performs extraction — it only defines shapes and the controlled
vocabulary that day-one schema must support.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# §5.1 Node types — exactly EIGHT. Compact core, rich edges.
# --------------------------------------------------------------------------- #


class NodeType(StrEnum):
    CHARACTER = "Character"
    PLACE = "Place"
    ORGANIZATION = "Organization"
    ITEM = "Item"
    ABILITY = "Ability"
    CONCEPT = "Concept"
    EVENT = "Event"
    TITLE = "Title"


# §5.2 Subtypes — a nullable node property. NULL is always valid.
# Species and Rank are Concept subtypes (NOT node types), per SPEC §5.1.
SUBTYPES: dict[NodeType, tuple[str, ...]] = {
    NodeType.ORGANIZATION: (
        "Faction", "Clan", "Sect", "Guild", "Kingdom", "Empire",
        "Army", "Cult", "Church", "Corporation", "School",
    ),
    NodeType.ABILITY: ("Spell", "Technique", "Skill", "Aspect", "Talent", "Passive", "Active"),
    NodeType.ITEM: ("Weapon", "Consumable", "Resource", "Treasure", "Relic", "Artifact"),
    NodeType.CONCEPT: (
        "System", "PowerSystem", "Language", "Species", "Rank",
        "Currency", "Law", "Phenomenon",
    ),
    NodeType.CHARACTER: ("Person", "Deity", "Creature", "Construct"),
    NodeType.PLACE: ("Region", "City", "Realm", "Building", "Landmark"),
    NodeType.EVENT: ("Battle", "Tournament", "Disaster", "Ritual", "Ceremony"),
    NodeType.TITLE: ("Honorary", "Political", "Religious", "Combat"),
}


# --------------------------------------------------------------------------- #
# §5.3 Relationship vocabulary — THREE tiers.
# --------------------------------------------------------------------------- #


class RelationTier(IntEnum):
    STRUCTURAL = 1  # GLiNER floor MUST produce these.
    SOCIAL = 2  # LLM enhancement layer adds these.
    IDENTITY = 3  # LLM-inferred; schema exists day one.


# Tier 1 — structural. GLiNER floor must produce; RelatedTo is the never-drop fallback.
TIER1_RELATIONS: tuple[str, ...] = (
    "AffiliatedWith", "LocatedIn", "MemberOf", "LeaderOf",
    "HasAbility", "OwnsItem", "HasTitle", "ParticipatedIn", "RelatedTo",
)

# Tier 2 — social / semantic. Added by the optional LLM layer.
TIER2_RELATIONS: tuple[str, ...] = (
    "Ally", "Enemy", "Rival", "Mentor", "Student",
    "Family", "Parent", "Child", "Sibling", "Spouse",
    "Romantic", "Betrayed", "Serves", "Killed", "Protects", "Fears", "Respects",
)

# Tier 3 — identity family. The showcase; LLM-inferred, fenced on revealed_chapter.
TIER3_RELATIONS: tuple[str, ...] = (
    "SAME_AS", "ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO",
)

RELATION_TIER: dict[str, RelationTier] = {
    **{r: RelationTier.STRUCTURAL for r in TIER1_RELATIONS},
    **{r: RelationTier.SOCIAL for r in TIER2_RELATIONS},
    **{r: RelationTier.IDENTITY for r in TIER3_RELATIONS},
}

ALL_RELATIONS: tuple[str, ...] = TIER1_RELATIONS + TIER2_RELATIONS + TIER3_RELATIONS


class ExtractionMethod(StrEnum):
    """Provenance: how an element entered the graph."""

    GLINER = "gliner"
    RULE = "rule"
    LLM = "llm"


# --------------------------------------------------------------------------- #
# Persisted shapes. Every node, edge, and property carries the universal reveal
# stamps (§5.4): first_seen_chapter (exists in text) + revealed_chapter (reader
# learns it). The fence keys visibility on revealed_chapter.
# --------------------------------------------------------------------------- #


class Work(BaseModel):
    id: int | None = None
    slug: str
    title: str


# --------------------------------------------------------------------------- #
# Source-data layer (Phase 1). Chapters + chunks are the raw ingested text from
# which everything else is derived. They are NOT graph elements, so they carry no
# reveal stamps — the reveal mechanism lives on nodes/edges/properties. Each row
# carries a content_hash for idempotent re-ingest.
# --------------------------------------------------------------------------- #


class Chapter(BaseModel):
    id: int | None = None
    work_id: int
    ordinal: int  # the reader-facing chapter number (drives the fence elsewhere)
    title: str | None = None
    clean_text: str  # canonical cleaned text; chunk offsets index into THIS
    content_hash: str
    source_path: str | None = None


class Chunk(BaseModel):
    """A sentence-aligned slice of a chapter's clean_text.

    Hard invariant (Phase 1): ``chapter.clean_text[char_start:char_end] == text``.
    """

    id: int | None = None
    chapter_id: int
    work_id: int
    ordinal: int  # position within the chapter
    char_start: int
    char_end: int
    text: str
    content_hash: str


class Node(BaseModel):
    id: int | None = None
    work_id: int
    type: NodeType
    name: str
    subtype: str | None = None
    importance: float = 0.0
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: ExtractionMethod
    evidence_span: str | None = None


class Edge(BaseModel):
    id: int | None = None
    work_id: int
    source_id: int
    target_id: int
    relation: str
    tier: RelationTier
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: ExtractionMethod
    evidence_span: str | None = None


class NodeProperty(BaseModel):
    """A reveal-stamped fact about a node (§5.4 property-level example).

    e.g. Klein's node exists from ch1, but {key: "rank", value: "Seer",
    revealed_chapter: 5} stays hidden until ch5.
    """

    id: int | None = None
    node_id: int
    key: str
    value: str
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: ExtractionMethod
    evidence_span: str | None = None


__all__ = [
    "ALL_RELATIONS",
    "RELATION_TIER",
    "SUBTYPES",
    "TIER1_RELATIONS",
    "TIER2_RELATIONS",
    "TIER3_RELATIONS",
    "Chapter",
    "Chunk",
    "Edge",
    "ExtractionMethod",
    "Node",
    "NodeProperty",
    "NodeType",
    "RelationTier",
    "Work",
]
