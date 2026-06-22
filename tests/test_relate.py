"""Phase 3: Tier-1 relationship extraction (proximity/rule, light venv)."""

from __future__ import annotations

from storyweave.db.models import (
    Chapter,
    ExtractionMethod,
    Mention,
    Node,
    NodeType,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.graph.builder import build_relationships, classify_relation


def _node(name: str, typ: NodeType) -> Node:
    return Node(
        work_id=1,
        type=typ,
        name=name,
        first_seen_chapter=1,
        revealed_chapter=1,
        extraction_method=ExtractionMethod.GLINER,
    )


def _setup(repo: Repository, clean_text: str, spans: list[tuple[str, NodeType, int, int]]) -> int:
    """Insert a one-chapter work with nodes + mentions at the given spans."""
    wid = repo.create_work(Work(slug="t", title="T"))
    cid = repo.add_chapter(
        Chapter(work_id=wid, ordinal=1, clean_text=clean_text, content_hash="h")
    )
    for ordinal, (name, typ, start, end) in enumerate(spans):
        nid = repo.add_node(
            Node(
                work_id=wid,
                type=typ,
                name=name,
                first_seen_chapter=1,
                revealed_chapter=1,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
        repo.add_mention(
            Mention(
                work_id=wid,
                chapter_id=cid,
                chapter_ordinal=1,
                ordinal=ordinal,
                surface=name,
                type=typ,
                char_start=start,
                char_end=end,
                score=0.9,
                node_id=nid,
            )
        )
    return wid


def test_classify_relation_type_pairs() -> None:
    char = _node("Wren", NodeType.CHARACTER)
    org = _node("the Coil", NodeType.ORGANIZATION)
    place = _node("Aldercross", NodeType.PLACE)

    _, _, rel = classify_relation(char, org, "Wren joined the Coil")
    assert rel == "MemberOf"
    _, _, rel = classify_relation(char, place, "Wren in Aldercross")
    assert rel == "LocatedIn"
    # Leadership cue promotes MemberOf -> LeaderOf, regardless of arg order.
    src, tgt, rel = classify_relation(org, char, "Veris led the Coil")
    assert rel == "LeaderOf"
    assert src.type is NodeType.CHARACTER and tgt.type is NodeType.ORGANIZATION


def test_two_characters_fall_back_to_relatedto() -> None:
    a = _node("Wren", NodeType.CHARACTER)
    b = _node("Dunmore", NodeType.CHARACTER)
    _, _, rel = classify_relation(a, b, "Wren met Dunmore")
    assert rel == "RelatedTo"


def test_build_relationships_from_cooccurrence() -> None:
    text = "Wren joined the Coil in Aldercross."
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _setup(
            repo,
            text,
            [
                ("Wren", NodeType.CHARACTER, 0, 4),
                ("the Coil", NodeType.ORGANIZATION, 12, 20),
                ("Aldercross", NodeType.PLACE, 24, 34),
            ],
        )
        report = build_relationships(wid, repo)

        relations = {e.relation for e in repo.list_edges(wid)}
        assert report.edges_added == 3
        assert "MemberOf" in relations  # Wren -> the Coil
        assert "LocatedIn" in relations  # Wren -> Aldercross, the Coil -> Aldercross
        for e in repo.list_edges(wid):
            assert e.extraction_method is ExtractionMethod.RULE
            assert e.first_seen_chapter == 1 and e.revealed_chapter == 1
            assert e.evidence_span


def test_window_excludes_far_pairs() -> None:
    # Two entities 400 chars apart; default window is 250 -> no edge.
    text = "Wren" + " " * 400 + "Aldercross"
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _setup(
            repo,
            text,
            [
                ("Wren", NodeType.CHARACTER, 0, 4),
                ("Aldercross", NodeType.PLACE, 404, 414),
            ],
        )
        report = build_relationships(wid, repo)
        assert report.edges_added == 0


def test_build_relationships_is_idempotent() -> None:
    text = "Wren joined the Coil."
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = _setup(
            repo,
            text,
            [
                ("Wren", NodeType.CHARACTER, 0, 4),
                ("the Coil", NodeType.ORGANIZATION, 12, 20),
            ],
        )
        first = build_relationships(wid, repo)
        second = build_relationships(wid, repo)
        assert first.edges_added == second.edges_added
        assert repo.count_edges(wid) == second.edges_added
