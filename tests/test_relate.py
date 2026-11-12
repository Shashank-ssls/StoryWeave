"""Phase 3: Tier-1 relationship extraction (proximity/rule, light venv)."""

from __future__ import annotations

from storyweave.db.models import (
    Chapter,
    Edge,
    ExtractionMethod,
    Mention,
    Node,
    NodeType,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.graph.builder import build_relationships, classify_relation
from storyweave.ingest.work_config import RelationConfig, WorkConfig


def rule_enabled() -> WorkConfig:
    """The co-occurrence builder is off by default (retrofit rule 5); these tests are
    about the rule itself, so they switch it on explicitly."""
    return WorkConfig(relations=RelationConfig(cooccurrence_enabled=True))


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
        report = build_relationships(wid, repo, rule_enabled())

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
        report = build_relationships(wid, repo, rule_enabled())
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
        first = build_relationships(wid, repo, rule_enabled())
        second = build_relationships(wid, repo, rule_enabled())
        assert first.edges_added == second.edges_added
        assert repo.count_edges(wid) == second.edges_added


# --------------------------------------------------------------------------- #
# Retrofit R1: co-occurrence is off by default, and a rule rebuild is scoped to
# the edges the rule builder owns.
# --------------------------------------------------------------------------- #


def test_cooccurrence_disabled_by_default_creates_no_edges() -> None:
    """The shipped default must produce zero rule edges (retrofit rule 5)."""
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
        # No config at all, and an explicitly-default config: both must be inert.
        assert build_relationships(wid, repo).edges_added == 0
        assert build_relationships(wid, repo, WorkConfig()).edges_added == 0
        assert repo.count_edges(wid) == 0
        assert RelationConfig().cooccurrence_enabled is False

        # Switching the flag on is the only way to get them, and it still works —
        # the builder is evidence, not dead code.
        assert build_relationships(wid, repo, rule_enabled()).edges_added == 3


def test_rule_rebuild_does_not_delete_other_producers_edges() -> None:
    """Toggling or re-running the rule builder must not touch relex/llm/curated edges."""
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
        ids = [n.id for n in repo.list_nodes(wid)]
        assert ids[0] is not None and ids[1] is not None

        # One edge from each of the other three producers (relex edges are stamped
        # `gliner`, being a GLiNER model), all on the same pair.
        for method, tier, relation in (
            (ExtractionMethod.GLINER, RelationTier.SOCIAL, "Serves"),
            (ExtractionMethod.LLM, RelationTier.IDENTITY, "SAME_AS"),
            (ExtractionMethod.CURATED, RelationTier.SOCIAL, "Mentor"),
        ):
            repo.add_edge(
                Edge(
                    work_id=wid,
                    source_id=ids[0],
                    target_id=ids[1],
                    relation=relation,
                    tier=tier,
                    first_seen_chapter=1,
                    revealed_chapter=1,
                    extraction_method=method,
                    evidence_span="ev",
                )
            )
        survivors = {(e.extraction_method, e.relation) for e in repo.list_edges(wid)}
        assert len(survivors) == 3

        # Rule ON: adds its own edge, keeps the other three.
        build_relationships(wid, repo, rule_enabled())
        after_on = [e for e in repo.list_edges(wid)]
        assert sum(1 for e in after_on if e.extraction_method is ExtractionMethod.RULE) == 1
        assert survivors <= {(e.extraction_method, e.relation) for e in after_on}

        # Rule re-run: still exactly one rule edge, others still there (idempotent).
        build_relationships(wid, repo, rule_enabled())
        assert sum(
            1 for e in repo.list_edges(wid) if e.extraction_method is ExtractionMethod.RULE
        ) == 1

        # Rule OFF: its own edges go, every other producer's edge survives untouched.
        build_relationships(wid, repo)
        remaining = repo.list_edges(wid)
        assert all(e.extraction_method is not ExtractionMethod.RULE for e in remaining)
        assert {(e.extraction_method, e.relation) for e in remaining} == survivors
