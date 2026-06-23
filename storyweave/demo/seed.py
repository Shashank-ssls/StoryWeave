"""Deterministic CC0 demo graph for the Phase-8 frontend slice — NO ML, NO LLM.

The frontend slice needs the signature reveal (Wren==Caelum's SECRET_IDENTITY edge
blooming at ch2) present in the served DB, but Tier-3 identity inference needs the LLM
(OFF by default). So this module hand-builds the `the-hollow-crown` graph through the
EXISTING repository API only — no new SQL, no schema change — mirroring the documented
gold facts of the CC0 sample (the same reveal chapters the deterministic identity tests
assert: SECRET_IDENTITY@2, ALIAS@3, TRANSMIGRATED_INTO@4). Everything here is CC0; it is
the only data the committed slice depends on. Real novels still go through the live
pipeline; this is reproducible demo fixture data, equivalent to the fence-test fixtures.

Reveal stamps are the whole point: every node/edge carries `revealed_chapter`, so the
fence (query/fence.py) blooms the graph exactly as the slider advances. The 8 node types
are all represented so the legend is meaningful.
"""

from __future__ import annotations

from storyweave.db.models import (
    Chapter,
    Edge,
    ExtractionMethod,
    Node,
    NodeProperty,
    NodeType,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository

DEMO_SLUG = "the-hollow-crown"
DEMO_TITLE = "The Hollow Crown"
GLINER = ExtractionMethod.GLINER
RULE = ExtractionMethod.RULE
LLM = ExtractionMethod.LLM
T1 = RelationTier.STRUCTURAL
T3 = RelationTier.IDENTITY

# (name, type, subtype, importance, first_seen=revealed, evidence) — all 8 types present.
_NODES: list[tuple[str, NodeType, str | None, float, int, str]] = [
    ("Wren", NodeType.CHARACTER, "Person", 1.0, 1, "Wren moved through Aldercross."),
    ("Aldercross", NodeType.PLACE, "City", 0.6, 1, "the night markets of Aldercross"),
    ("the Glasswound", NodeType.CONCEPT, "Phenomenon", 0.5, 1, "glass towers that do not exist"),
    ("the heron ring", NodeType.ITEM, "Relic", 0.4, 1, "a heron ring he kept"),
    ("Glass-sight", NodeType.ABILITY, "Aspect", 0.4, 1, "he saw glass towers"),
    ("the Coil", NodeType.ORGANIZATION, "Faction", 0.5, 1, "the Coil watched the gates"),
    ("Prince Caelum", NodeType.CHARACTER, "Person", 1.0, 2, "Prince Caelum Veyle, son of Maela"),
    ("Queen Maela", NodeType.CHARACTER, "Person", 0.6, 2, "only son of Queen Maela"),
    ("Ser Dunmore", NodeType.CHARACTER, "Person", 0.6, 2, "Ser Dunmore at every gate"),
    ("Prince", NodeType.TITLE, "Political", 0.4, 2, "Prince Caelum Veyle"),
    ("the Gray Sparrow", NodeType.CHARACTER, "Person", 0.8, 3, "the message named the Sparrow"),
    ("Lady Veris", NodeType.CHARACTER, "Person", 0.8, 3, "the same person as Lady Veris"),
    ("the Alliance", NodeType.EVENT, "Ceremony", 0.5, 4, "Ser Dunmore knelt"),
]

# (source, target, relation, tier, revealed, method, evidence). Structural edges reveal
# when both endpoints are revealed; identity edges carry the GOLD reveal chapter.
_EDGES: list[tuple[str, str, str, RelationTier, int, ExtractionMethod, str]] = [
    ("Wren", "Aldercross", "LocatedIn", T1, 1, RULE, "Wren moved through Aldercross"),
    ("Wren", "Glass-sight", "HasAbility", T1, 1, RULE, "he saw glass towers"),
    ("Wren", "the heron ring", "OwnsItem", T1, 1, RULE, "the heron ring he kept"),
    ("Wren", "the Glasswound", "RelatedTo", T1, 1, RULE, "the Glasswound's visions"),
    ("the Coil", "Aldercross", "LocatedIn", T1, 1, RULE, "the Coil in Aldercross"),
    ("Prince Caelum", "Prince", "HasTitle", T1, 2, RULE, "Prince Caelum Veyle"),
    ("Prince Caelum", "Queen Maela", "RelatedTo", T1, 2, RULE, "only son of Queen Maela"),
    ("Ser Dunmore", "Prince Caelum", "RelatedTo", T1, 2, RULE, "Dunmore served the prince"),
    ("the Gray Sparrow", "the Coil", "AffiliatedWith", T1, 3, RULE, "the Sparrow and the Coil"),
    ("Lady Veris", "the Gray Sparrow", "RelatedTo", T1, 3, RULE, "Veris and the Sparrow"),
    ("Ser Dunmore", "the Alliance", "ParticipatedIn", T1, 4, RULE, "Ser Dunmore knelt"),
    # Tier-3 identity — the showcase. Layered reveal on the Wren/Caelum pair (2 and 4).
    ("Wren", "Prince Caelum", "SECRET_IDENTITY", T3, 2, LLM, "Wren was Caelum."),
    ("the Gray Sparrow", "Lady Veris", "ALIAS", T3, 3, LLM, "the Sparrow and Veris were one"),
    ("Wren", "Prince Caelum", "TRANSMIGRATED_INTO", T3, 4, LLM, "an older soul, drowned prince"),
]

# (node, key, value, revealed, evidence) — a property revealed LATER than its node, to
# exercise the property-level both-rule fence in the projection.
_PROPERTIES: list[tuple[str, str, str, int, str]] = [
    ("Prince Caelum", "fate", "drowned at six", 2, "drowned at six"),
    ("Wren", "true name", "Caelum Veyle", 2, "Wren was Caelum."),
    ("Wren", "origin", "an older soul, not of this world", 4, "poured into the drowned prince"),
]


def seed_hollow_crown(repo: Repository) -> int:
    """Build the deterministic CC0 demo graph; return the work id.

    Raises if the slug already exists (seed into a fresh DB — the demo is rebuildable).
    """
    if repo.get_work_by_slug(DEMO_SLUG) is not None:
        raise ValueError(
            f"work '{DEMO_SLUG}' already exists in this DB; seed into a fresh --db file"
        )
    work_id = repo.create_work(Work(slug=DEMO_SLUG, title=DEMO_TITLE))

    # Four chapters so the slider has range 1..4 (chunks/text are not needed for the slice).
    for ordinal in (1, 2, 3, 4):
        repo.add_chapter(
            Chapter(
                work_id=work_id,
                ordinal=ordinal,
                title=f"Chapter {ordinal}",
                clean_text=f"[demo chapter {ordinal}]",
                content_hash=f"demo-{ordinal}",
            )
        )

    ids: dict[str, int] = {}
    for name, ntype, subtype, importance, chapter, evidence in _NODES:
        ids[name] = repo.add_node(
            Node(
                work_id=work_id,
                type=ntype,
                name=name,
                subtype=subtype,
                importance=importance,
                first_seen_chapter=chapter,
                revealed_chapter=chapter,
                extraction_method=GLINER,
                evidence_span=evidence,
            )
        )

    for src, tgt, relation, tier, revealed, method, evidence in _EDGES:
        repo.add_edge(
            Edge(
                work_id=work_id,
                source_id=ids[src],
                target_id=ids[tgt],
                relation=relation,
                tier=tier,
                # Identity reveals SHIFT (entities exist earlier; the reader only connects
                # them at `revealed`); structural edges reveal when both endpoints do. The
                # fence keys on revealed_chapter, so first_seen is pinned to it here.
                first_seen_chapter=revealed,
                revealed_chapter=revealed,
                extraction_method=method,
                evidence_span=evidence,
            )
        )

    for node_name, key, value, revealed, evidence in _PROPERTIES:
        repo.add_node_property(
            NodeProperty(
                node_id=ids[node_name],
                key=key,
                value=value,
                first_seen_chapter=revealed,
                revealed_chapter=revealed,
                extraction_method=LLM,
                evidence_span=evidence,
            )
        )

    return work_id
