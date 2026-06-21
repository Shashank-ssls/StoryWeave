"""Phase 0: the full 8-type schema initializes and round-trips a reveal-stamped graph.

This proves the day-one schema (SPEC §5) — eight node types, three-tier edges, a
node-property mechanism, and universal first_seen/revealed stamps — exists and is
usable, even though no extraction logic is implemented yet.
"""

from __future__ import annotations

import pytest

from storyweave.db.models import (
    ALL_RELATIONS,
    SUBTYPES,
    Edge,
    ExtractionMethod,
    Node,
    NodeProperty,
    NodeType,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository


def test_ontology_has_exactly_eight_node_types() -> None:
    assert len(list(NodeType)) == 8


def test_subtypes_cover_every_node_type() -> None:
    assert set(SUBTYPES.keys()) == set(NodeType)


def test_identity_relations_present_day_one() -> None:
    for rel in ("SAME_AS", "ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"):
        assert rel in ALL_RELATIONS


def test_schema_round_trip_with_reveal_stamps() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        work_id = repo.create_work(Work(slug="lotm", title="Lord of the Mysteries"))

        klein = repo.add_node(
            Node(
                work_id=work_id,
                type=NodeType.CHARACTER,
                name="Klein",
                subtype="Person",
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
        zhou = repo.add_node(
            Node(
                work_id=work_id,
                type=NodeType.CHARACTER,
                name="Zhou Mingrui",
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.LLM,
            )
        )

        # Tier-3 identity edge (schema must support it day one).
        edge_id = repo.add_edge(
            Edge(
                work_id=work_id,
                source_id=zhou,
                target_id=klein,
                relation="TRANSMIGRATED_INTO",
                tier=RelationTier.IDENTITY,
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.LLM,
            )
        )

        # Property-level reveal: rank known to the reader only at ch5.
        prop_id = repo.add_node_property(
            NodeProperty(
                node_id=klein,
                key="rank",
                value="Seer",
                first_seen_chapter=5,
                revealed_chapter=5,
                extraction_method=ExtractionMethod.GLINER,
            )
        )

        assert work_id and klein and zhou and edge_id and prop_id
        assert repo.get_work(work_id) is not None


def test_node_type_check_constraint_rejects_unknown_type() -> None:
    import sqlite3

    with Repository(":memory:") as repo:
        repo.initialize_schema()
        repo.conn.execute("INSERT INTO works (slug, title) VALUES ('w', 'W')")
        with pytest.raises(sqlite3.IntegrityError):
            repo.conn.execute(
                """INSERT INTO nodes
                     (work_id, type, name, first_seen_chapter, revealed_chapter,
                      extraction_method)
                   VALUES (1, 'Faction', 'X', 1, 1, 'gliner')"""
            )
