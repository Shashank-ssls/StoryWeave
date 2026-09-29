"""Pydantic mirrors of the persisted schema + the full 8-type ontology vocabulary.

This module is the single Python-side definition of the ontology (SPEC §5):
the eight node types, the per-type subtype hints, and the three-tier relationship
vocabulary. The SQL schema in :mod:`storyweave.db.repository` enforces the same
node-type and tier constraints; these mirrors keep the application layer honest.

Nothing here performs extraction — it only defines shapes and the controlled
vocabulary that day-one schema must support.
"""

from __future__ import annotations

from dataclasses import dataclass
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


# --------------------------------------------------------------------------- #
# Retrofit R3: STORED vocabulary vs. GRAPH vocabulary.
#
# v1 measured 16 of 44 entity errors as type disagreement across eight types, so the
# retrofit draws the graph with four. Rather than shrink the stored enum — which would
# make the frozen v1 database and the seeded Hollow Crown fixture unreadable, breaking
# rule I2 — there are two vocabularies and one mapping between them:
#
#   NodeType (== StoredNodeType)  the eight values the SCHEMA accepts. Unchanged: the
#                                 nodes.type CHECK constraint and Node(**row) validation
#                                 are exactly what they were, so every historical row
#                                 still loads. No migration rewrites anything.
#   GraphNodeType                 the four values new extraction may WRITE and the graph
#                                 payload may SERVE.
#
# Enforcement is in three independent places, so no single omission can leak a legacy
# type into the graph:
#   (a) nlp/labels.py prompts GLiNER with the four types only  -> nothing new is created;
#   (b) Repository.add_node rejects a non-graph type by default -> nothing new is stored;
#   (c) repository.list_graph_nodes_revealed adds a display clause `type IN (...)` AFTER
#       the fence clause, never merged with it                  -> nothing legacy is served.
# --------------------------------------------------------------------------- #


class GraphNodeType(StrEnum):
    """The four types the graph draws. A strict subset of :class:`NodeType`'s values."""

    CHARACTER = "Character"
    ORGANIZATION = "Organization"
    PLACE = "Place"
    ITEM = "Item"


#: Alias making the distinction explicit at call sites that mean "whatever is stored".
StoredNodeType = NodeType

#: The four graph types as stored-enum members, for SQL and comparisons.
GRAPH_NODE_TYPES: tuple[NodeType, ...] = (
    NodeType.CHARACTER,
    NodeType.ORGANIZATION,
    NodeType.PLACE,
    NodeType.ITEM,
)


class LegacyTypeFate(StrEnum):
    """What R3 does with a v1 node type that is no longer drawn."""

    #: Still a graph node, still drawn. (The four survivors.)
    GRAPH_NODE = "graph_node"
    #: Not a node. Existing rows are kept and remain searchable via `mentions`, but
    #: they are never served in a graph payload, and nothing new of this type is written.
    NOT_A_NODE = "not_a_node"
    #: Becomes an `entity_labels` row on the person the text links it to; if the text
    #: never links it to anyone, it is simply not served.
    BECOMES_LABEL = "becomes_label"


#: The v1 fate of every stored type — the ONE place this is written down.
LEGACY_TYPE_MAP: dict[NodeType, LegacyTypeFate] = {
    NodeType.CHARACTER: LegacyTypeFate.GRAPH_NODE,
    NodeType.ORGANIZATION: LegacyTypeFate.GRAPH_NODE,
    NodeType.PLACE: LegacyTypeFate.GRAPH_NODE,
    NodeType.ITEM: LegacyTypeFate.GRAPH_NODE,
    # Abilities, concepts and events were the worst of the type confusion: a power
    # system, a sensory abstraction and an unnamed past occurrence are not people,
    # places or things, and GLiNER cannot tell them apart zero-shot. Their rows stay
    # (they are real text spans, and search still finds them) but they are not drawn.
    NodeType.ABILITY: LegacyTypeFate.NOT_A_NODE,
    NodeType.CONCEPT: LegacyTypeFate.NOT_A_NODE,
    NodeType.EVENT: LegacyTypeFate.NOT_A_NODE,
    # A title is not a separate being from the person who holds it: "the Warden" is a
    # name for someone, so it belongs in entity_labels, gated on the chapter the text
    # connects the two.
    NodeType.TITLE: LegacyTypeFate.BECOMES_LABEL,
}


def is_graph_type(node_type: NodeType) -> bool:
    """True when this stored type is one the graph draws."""
    return LEGACY_TYPE_MAP[node_type] is LegacyTypeFate.GRAPH_NODE


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


# --------------------------------------------------------------------------- #
# Retrofit R4 — the CLOSED relation list. Twelve relations, two rings.
#
# Same shape as R3's two node vocabularies: the STORED vocabulary above is left
# untouched (so the frozen v1 baseline and the Hollow Crown fixture still load and
# still satisfy the `edges.relation` CHECK), and this is the vocabulary NEW extraction
# may write and the payload may serve. `LEGACY_RELATION_MAP` is the single place
# recording each old relation's fate, exactly as `LEGACY_TYPE_MAP` does for types.
# --------------------------------------------------------------------------- #


class Relation(StrEnum):
    """The twelve relations the retrofit graph may create (retrofit rule 3)."""

    # Ring 1 — drawn in the default graph.
    KIN_OF = "KIN_OF"
    ROMANTIC_WITH = "ROMANTIC_WITH"
    ALLY_OF = "ALLY_OF"
    ENEMY_OF = "ENEMY_OF"
    SERVES = "SERVES"
    MENTOR_OF = "MENTOR_OF"
    KILLED = "KILLED"
    SAME_AS = "SAME_AS"
    # Ring 2 — overlays only.
    MEMBER_OF = "MEMBER_OF"
    LEADS = "LEADS"
    OWNS = "OWNS"
    LOCATED_IN = "LOCATED_IN"


#: Ring 1: the default graph. Ring 2: overlays only (retrofit rule 3).
RING1_RELATIONS: tuple[Relation, ...] = (
    Relation.KIN_OF, Relation.ROMANTIC_WITH, Relation.ALLY_OF, Relation.ENEMY_OF,
    Relation.SERVES, Relation.MENTOR_OF, Relation.KILLED, Relation.SAME_AS,
)
RING2_RELATIONS: tuple[Relation, ...] = (
    Relation.MEMBER_OF, Relation.LEADS, Relation.OWNS, Relation.LOCATED_IN,
)
RELATIONS: tuple[Relation, ...] = RING1_RELATIONS + RING2_RELATIONS

#: A relation's storage tier, so R4 edges keep flowing through the existing `tier`
#: column and its CHECK. Identity is tier 3; the ring-2 structural relations are tier 1;
#: everything else is social.
RELATION_RING: dict[Relation, int] = {
    **{r: 1 for r in RING1_RELATIONS},
    **{r: 2 for r in RING2_RELATIONS},
}


class RelationGrade(StrEnum):
    """How well the evidence quote supports the edge (R4 task 3f).

    STATED: the quote names BOTH participants (a label of each) AND carries a relation
    cue word. This is the only grade the graph serves. INFERRED: everything else that
    passed the validator — kept in the database as evidence and for recall diagnostics,
    never drawn.
    """

    STATED = "STATED"
    INFERRED = "INFERRED"


@dataclass(frozen=True)
class RelationSpec:
    """Domain/range and algebra for one relation (R4 task 1's table, as data)."""

    head: frozenset[NodeType]
    tail: frozenset[NodeType]
    symmetric: bool
    closable: bool


_C = NodeType.CHARACTER
_O = NodeType.ORGANIZATION
_P = NodeType.PLACE
_I = NodeType.ITEM

#: The R4 domain/range table, verbatim from docs/retrofit/R4_closed_relations_validator.md.
DOMAIN_RANGE: dict[Relation, RelationSpec] = {
    Relation.KIN_OF: RelationSpec(frozenset({_C}), frozenset({_C}), False, False),
    Relation.ROMANTIC_WITH: RelationSpec(frozenset({_C}), frozenset({_C}), True, True),
    Relation.ALLY_OF: RelationSpec(frozenset({_C, _O}), frozenset({_C, _O}), True, True),
    Relation.ENEMY_OF: RelationSpec(frozenset({_C, _O}), frozenset({_C, _O}), True, True),
    Relation.SERVES: RelationSpec(frozenset({_C}), frozenset({_C, _O}), False, True),
    Relation.MENTOR_OF: RelationSpec(frozenset({_C}), frozenset({_C}), False, True),
    Relation.KILLED: RelationSpec(frozenset({_C}), frozenset({_C}), False, False),
    Relation.SAME_AS: RelationSpec(frozenset({_C}), frozenset({_C}), True, False),
    Relation.MEMBER_OF: RelationSpec(frozenset({_C}), frozenset({_O}), False, True),
    Relation.LEADS: RelationSpec(frozenset({_C}), frozenset({_O, _P}), False, True),
    Relation.OWNS: RelationSpec(frozenset({_C, _O}), frozenset({_I}), False, True),
    Relation.LOCATED_IN: RelationSpec(
        frozenset({_C, _O, _P}), frozenset({_P}), False, True
    ),
}

#: Relations whose endpoints are stored order-independently (head_id < tail_id).
SYMMETRIC_R4_RELATIONS: frozenset[Relation] = frozenset(
    r for r, spec in DOMAIN_RANGE.items() if spec.symmetric
)


class LegacyRelationFate(StrEnum):
    """What R4 does with each of v1's fifteen stored relation names."""

    MAPS = "MAPS"  # 1:1 (or reversed) onto one of the twelve
    BECOMES_LABEL = "BECOMES_LABEL"  # belongs in entity_labels, never an edge
    DROPPED = "DROPPED"  # outside the closed list; logged, never created


#: Old relation -> (fate, new relation or None, reverse the endpoints?).
#: The single audit point for R4 task 2. `subtype` preserves the original name for the
#: identity family, and `kin_role` preserves it for kinship, so nothing is lost.
LEGACY_RELATION_MAP: dict[str, tuple[LegacyRelationFate, Relation | None, bool]] = {
    # -- Tier 1 structural --
    "MemberOf": (LegacyRelationFate.MAPS, Relation.MEMBER_OF, False),
    "LeaderOf": (LegacyRelationFate.MAPS, Relation.LEADS, False),
    "LocatedIn": (LegacyRelationFate.MAPS, Relation.LOCATED_IN, False),
    "OwnsItem": (LegacyRelationFate.MAPS, Relation.OWNS, False),
    "HasTitle": (LegacyRelationFate.BECOMES_LABEL, None, False),
    "AffiliatedWith": (LegacyRelationFate.DROPPED, None, False),
    "HasAbility": (LegacyRelationFate.DROPPED, None, False),
    "ParticipatedIn": (LegacyRelationFate.DROPPED, None, False),
    "RelatedTo": (LegacyRelationFate.DROPPED, None, False),
    # -- Tier 2 social --
    "Ally": (LegacyRelationFate.MAPS, Relation.ALLY_OF, False),
    "Enemy": (LegacyRelationFate.MAPS, Relation.ENEMY_OF, False),
    "Mentor": (LegacyRelationFate.MAPS, Relation.MENTOR_OF, False),
    "Student": (LegacyRelationFate.MAPS, Relation.MENTOR_OF, True),  # reversed
    "Parent": (LegacyRelationFate.MAPS, Relation.KIN_OF, False),
    "Child": (LegacyRelationFate.MAPS, Relation.KIN_OF, False),
    "Sibling": (LegacyRelationFate.MAPS, Relation.KIN_OF, False),
    "Spouse": (LegacyRelationFate.MAPS, Relation.KIN_OF, False),
    "Family": (LegacyRelationFate.MAPS, Relation.KIN_OF, False),
    "Romantic": (LegacyRelationFate.MAPS, Relation.ROMANTIC_WITH, False),
    "Serves": (LegacyRelationFate.MAPS, Relation.SERVES, False),
    "Killed": (LegacyRelationFate.MAPS, Relation.KILLED, False),
    "Rival": (LegacyRelationFate.DROPPED, None, False),
    "Betrayed": (LegacyRelationFate.DROPPED, None, False),
    "Protects": (LegacyRelationFate.DROPPED, None, False),
    "Fears": (LegacyRelationFate.DROPPED, None, False),
    "Respects": (LegacyRelationFate.DROPPED, None, False),
    # -- Tier 3 identity: all collapse to SAME_AS, original kept as `subtype` --
    "SAME_AS": (LegacyRelationFate.MAPS, Relation.SAME_AS, False),
    "SECRET_IDENTITY": (LegacyRelationFate.MAPS, Relation.SAME_AS, False),
    "REINCARNATION": (LegacyRelationFate.MAPS, Relation.SAME_AS, False),
    "TRANSMIGRATED_INTO": (LegacyRelationFate.MAPS, Relation.SAME_AS, False),
    "ALIAS": (LegacyRelationFate.BECOMES_LABEL, None, False),
}

# Every stored relation name has a recorded fate: a new name cannot be added to the
# stored vocabulary without deciding what the retrofit graph does with it.
assert set(LEGACY_RELATION_MAP) == set(ALL_RELATIONS), (
    "LEGACY_RELATION_MAP must decide the fate of every stored relation"
)
# The twelve are reachable: each is either a map target or SAME_AS's family.
assert set(RELATIONS) >= {
    new for _fate, new, _rev in LEGACY_RELATION_MAP.values() if new is not None
}


class ExtractionMethod(StrEnum):
    """Provenance: how an element entered the graph.

    ``CURATED`` (integration phase, I3): a Tier-2/Tier-3 record hand-written from a
    story bible in place of a real LLM run (the LLM stays off per rule #5/I3). Distinct
    from ``LLM`` on purpose — labeling a hand-authored record ``llm`` would claim a
    model produced it when none ever ran. (The seeded Hollow Crown demo predates this
    distinction and still labels its own hand-built identity edges ``llm``; it is
    unchanged per the integration phase's I2 rule — the two demos use different,
    documented conventions rather than retrofitting Hollow Crown's history.)
    """

    GLINER = "gliner"
    RULE = "rule"
    LLM = "llm"
    CURATED = "curated"


# --------------------------------------------------------------------------- #
# Persisted shapes. Every node, edge, and property carries the universal reveal
# stamps (§5.4): first_seen_chapter (exists in text) + revealed_chapter (reader
# learns it). The fence keys visibility on revealed_chapter.
# --------------------------------------------------------------------------- #


class Work(BaseModel):
    id: int | None = None
    slug: str
    title: str


class Arc(BaseModel):
    """A named chapter range (D6, integration phase). Structural, not extracted —
    no provenance/reveal stamps of its own. Fencing (F6) is on the NAME only: an
    arc's chapter range is never spoiler-bearing by itself (it's just numbers), but
    its title can be, so `query/fence.py` redacts the name until the arc has started
    (``start_chapter <= the reader's bookmark``); the range still shows as
    "Arc N · chapters a-b" so the chapter picker can lay out the whole book.
    """

    id: int | None = None
    work_id: int
    ordinal: int
    name: str
    start_chapter: int
    end_chapter: int


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


class Mention(BaseModel):
    """A raw GLiNER candidate (Phase 2), persisted BEFORE alias clustering.

    Offsets index into the chapter's clean_text. ``node_id`` is backfilled once the
    mention is clustered into a canonical entity (node).
    """

    id: int | None = None
    work_id: int
    chapter_id: int
    chapter_ordinal: int
    ordinal: int  # index within the chapter's candidate list
    surface: str
    type: NodeType
    subtype: str | None = None
    char_start: int
    char_end: int
    score: float
    extraction_method: ExtractionMethod = ExtractionMethod.GLINER
    node_id: int | None = None


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
    """One relation between two nodes, with its reveal stamps and its evidence.

    The seven fields below ``evidence_span`` are retrofit R4 and all default, so a row
    from a pre-R4 database (the frozen v1 baseline, the Hollow Crown fixture) still
    validates unchanged — exactly the R3 `entity_labels` precedent.

    ``weight`` is why R4 has no duplicate edges: repeat evidence for the same
    (work, relation, head, tail) increments the weight and keeps the EARLIEST quote,
    rather than inserting a second row. ``quote`` is the verbatim citation the validator
    checked against clean text; ``grade`` says whether that quote names both
    participants (retrofit rule 4).
    """

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
    # --- retrofit R4 ---
    weight: int = 1
    grade: RelationGrade | None = None
    quote: str | None = None
    quote_chapter: int | None = None
    kin_role: str | None = None  # "father", "niece", ... for KIN_OF
    surface_term: str | None = None  # the cue word actually found in the quote
    subtype: str | None = None  # the original name for the SAME_AS family


class NodeSalience(BaseModel):
    """One node's importance rank at one chapter (retrofit R6).

    A row per (node, chapter) on purpose. The rank at chapter n is computed only from
    chapters <= n (retrofit rule 7), so a single book-wide rank would be wrong twice: it
    would be a spoiler side channel telling the reader who matters later, and it could
    not answer "who are the main twenty at chapter 5?" at all.

    This is DISPLAY data, never safety data. The payload query filters on ``rank`` in a
    clause that comes after the fence and is commented as a display clause.
    """

    node_id: int
    chapter: int
    score: float
    rank: int


class LabelKind(StrEnum):
    """What kind of name an :class:`EntityLabel` is."""

    FULL = "full"  # the fullest form the text gives: "Warden-Captain Orin Drask"
    SHORT = "short"  # a shortening of the full form: "Drask", "Orin"
    TITLE = "title"  # a title/office held by the person: "the Warden"
    EPITHET = "epithet"  # a by-name the text uses for them: "the Gray Sparrow"
    DESCRIPTION = "description"  # a descriptive reference: "the older Warden"


class EntityLabel(BaseModel):
    """One chapter-gated name for an entity (retrofit R3).

    An entity does not have *a* name, it has names the reader acquires over time, so a
    display name is a function of the chapter. This table is therefore a **FENCE
    SURFACE**: a label revealed at chapter k must not appear in any payload at k-1, or
    the graph leaks a name the reader has not been told yet (a title linking "the
    Warden" to a person is exactly the kind of reveal the fence exists for).

    ``is_primary`` marks the label extraction chose as canonical; the display name at
    chapter n is the most recently revealed visible label, preferring a primary one.
    ``quote`` is the verbatim evidence for the label, required for anything the text
    had to *connect* (a title), which is also what R4's validator reads.
    """

    id: int | None = None
    entity_id: int
    label: str
    kind: LabelKind
    revealed_chapter: int
    is_primary: bool = False
    quote: str | None = None


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
    "DOMAIN_RANGE",
    "LEGACY_RELATION_MAP",
    "RELATIONS",
    "RELATION_RING",
    "RING1_RELATIONS",
    "RING2_RELATIONS",
    "SYMMETRIC_R4_RELATIONS",
    "LegacyRelationFate",
    "Relation",
    "RelationGrade",
    "RelationSpec",
    "RELATION_TIER",
    "SUBTYPES",
    "TIER1_RELATIONS",
    "TIER2_RELATIONS",
    "TIER3_RELATIONS",
    "Arc",
    "Chapter",
    "Chunk",
    "Edge",
    "ExtractionMethod",
    "Mention",
    "Node",
    "NodeSalience",
    "NodeProperty",
    "NodeType",
    "RelationTier",
    "Work",
]
