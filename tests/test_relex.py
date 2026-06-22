"""Phase 7a: Tier-2 social relations via GLiNER-RelEx.

The light tests inject a fake extractor (RelexProtocol) so the whole orchestration —
anchoring, persistence, idempotency, fencing, graceful degradation — runs under the
light .venv with zero ML. One ML-gated test loads the real relex checkpoint.
"""

from __future__ import annotations

import pytest

from storyweave.db.models import (
    TIER2_RELATIONS,
    Chapter,
    Chunk,
    ExtractionMethod,
    Mention,
    Node,
    NodeType,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.graph.builder import build_relationships
from storyweave.nlp.relex import (
    RELATION_PROMPTS,
    RelationSpan,
    SocialReport,
    extract_social_relations,
)
from storyweave.query import fence


class FakeRelex:
    """A deterministic RelexProtocol stand-in (no model)."""

    def __init__(self, spans: list[RelationSpan], *, raise_on_call: bool = False) -> None:
        self._spans = spans
        self._raise = raise_on_call
        self.calls = 0

    def extract(self, text: str) -> list[RelationSpan]:
        self.calls += 1
        if self._raise:
            raise RuntimeError("simulated model failure")
        # Return the canned spans once (single chunk) — idempotency is the orchestrator's job.
        return list(self._spans)


def _setup_work(
    repo: Repository,
    nodes: list[tuple[str, NodeType, int]],  # (name, type, revealed_chapter)
    text: str = "placeholder chapter text",
) -> tuple[int, dict[str, int]]:
    """One-chapter work with one chunk and the given nodes (each with a mention)."""
    wid = repo.create_work(Work(slug="t", title="T"))
    cid = repo.add_chapter(Chapter(work_id=wid, ordinal=1, clean_text=text, content_hash="h"))
    repo.add_chunk(
        Chunk(
            chapter_id=cid, work_id=wid, ordinal=0,
            char_start=0, char_end=len(text), text=text, content_hash="c",
        )
    )
    name_to_id: dict[str, int] = {}
    for i, (name, typ, revealed) in enumerate(nodes):
        nid = repo.add_node(
            Node(
                work_id=wid, type=typ, name=name,
                first_seen_chapter=1, revealed_chapter=revealed,
                extraction_method=ExtractionMethod.GLINER,
            )
        )
        name_to_id[name] = nid
        repo.add_mention(
            Mention(
                work_id=wid, chapter_id=cid, chapter_ordinal=1, ordinal=i,
                surface=name, type=typ, char_start=0, char_end=len(name),
                score=0.9, node_id=nid,
            )
        )
    return wid, name_to_id


def test_relation_prompts_stay_within_tier2_vocab() -> None:
    """Every prompt maps to a real Tier-2 relation (no drift from the ontology)."""
    assert set(RELATION_PROMPTS.values()) <= set(TIER2_RELATIONS)


def test_social_edges_anchor_persist_and_stamp() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, ids = _setup_work(
            repo,
            [("Wren", NodeType.CHARACTER, 1), ("the Coil", NodeType.ORGANIZATION, 1)],
        )
        fake = FakeRelex(
            [RelationSpan("Wren", "Serves", "the Coil", 0.95, "Wren worked for the Coil")]
        )
        report = extract_social_relations(wid, repo, extractor=fake)

        assert report.edges_added == 1 and not report.degraded
        edges = repo.list_edges_by_tier(wid, RelationTier.SOCIAL)
        assert len(edges) == 1
        e = edges[0]
        assert e.relation == "Serves"
        assert e.source_id == ids["Wren"] and e.target_id == ids["the Coil"]
        assert e.tier is RelationTier.SOCIAL
        assert e.extraction_method is ExtractionMethod.GLINER  # a GLiNER model
        assert e.first_seen_chapter == 1 and e.revealed_chapter == 1  # stated relation
        assert e.evidence_span


def test_unanchored_span_makes_no_phantom_edge() -> None:
    """A relation to a span the floor never grounded yields no edge (no phantom nodes)."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_work(repo, [("Wren", NodeType.CHARACTER, 1)])
        fake = FakeRelex(
            [RelationSpan("Wren", "Serves", "Nonexistent Person", 0.9, "ev")]
        )
        report = extract_social_relations(wid, repo, extractor=fake)
        assert report.edges_added == 0
        assert repo.count_nodes(wid) == 1  # nothing invented


def test_symmetric_relation_is_deduped() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_work(
            repo, [("Veris", NodeType.CHARACTER, 1), ("Maela", NodeType.CHARACTER, 1)]
        )
        fake = FakeRelex(
            [
                RelationSpan("Veris", "Ally", "Maela", 0.8, "friends"),
                RelationSpan("Maela", "Ally", "Veris", 0.7, "friends"),
            ]
        )
        report = extract_social_relations(wid, repo, extractor=fake)
        assert report.edges_added == 1  # A-Ally-B == B-Ally-A


def test_tier1_floor_untouched_and_tier2_idempotent() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_work(
            repo,
            [("Wren", NodeType.CHARACTER, 1), ("the Coil", NodeType.ORGANIZATION, 1)],
            text="Wren joined the Coil.",
        )
        # Tier-1 structural floor (rule edges).
        t1 = build_relationships(wid, repo)
        assert t1.edges_added >= 1
        tier1_count = repo.count_edges(wid)

        fake = FakeRelex(
            [RelationSpan("Wren", "Serves", "the Coil", 0.9, "ev")]
        )
        first = extract_social_relations(wid, repo, extractor=fake)
        second = extract_social_relations(wid, repo, extractor=fake)

        assert first.edges_added == second.edges_added == 1
        # Tier-1 edges survived both Tier-2 rebuilds.
        assert len(repo.list_edges_by_tier(wid, RelationTier.STRUCTURAL)) == tier1_count
        # Tier-2 did not duplicate.
        assert len(repo.list_edges_by_tier(wid, RelationTier.SOCIAL)) == 1


def test_tier2_edge_passes_through_the_fence() -> None:
    """A Tier-2 edge to a late-revealed node is hidden until both endpoints are revealed."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        # Veris revealed ch1, the Hollow Crown's regent revealed ch3.
        wid, ids = _setup_work(
            repo,
            [("Veris", NodeType.CHARACTER, 1), ("Halvard", NodeType.CHARACTER, 3)],
        )
        fake = FakeRelex(
            [RelationSpan("Halvard", "Betrayed", "Veris", 0.9, "ev")]
        )
        extract_social_relations(wid, repo, extractor=fake)

        # No new fence path: visible_edges enforces the both-endpoints rule on Tier-2 too.
        assert fence.visible_edges(repo, wid, 2) == []  # Halvard not yet revealed
        visible = fence.visible_edges(repo, wid, 3)
        assert len(visible) == 1 and visible[0].relation == "Betrayed"


def test_graceful_degradation_keeps_the_floor() -> None:
    """If relex fails mid-run, the report degrades and the Tier-1 floor is intact (rule #4)."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid, _ = _setup_work(
            repo,
            [("Wren", NodeType.CHARACTER, 1), ("the Coil", NodeType.ORGANIZATION, 1)],
            text="Wren joined the Coil.",
        )
        build_relationships(wid, repo)
        tier1_count = repo.count_edges(wid)

        broken = FakeRelex([], raise_on_call=True)
        report: SocialReport = extract_social_relations(wid, repo, extractor=broken)

        assert report.degraded is True
        assert report.edges_added == 0
        # The structural floor and the graph it powers are unaffected.
        assert repo.count_edges(wid) == tier1_count
        assert len(fence.visible_edges(repo, wid, 1)) == tier1_count


# --------------------------------------------------------------------------- #
# ML-gated: the real GLiNER-RelEx checkpoint (runs only under .venv-ml).
# --------------------------------------------------------------------------- #


def test_real_relex_extracts_tier2_relation() -> None:
    pytest.importorskip("gliner")
    from storyweave.nlp.relex import RelexExtractor

    ext = RelexExtractor()
    text = "Lady Veris betrayed the Coil and served Prince Caelum, who mentored the squire Wren."
    spans = ext.extract(text)

    assert spans, "relex produced no relations on a clearly relational sentence"
    relations = {s.relation for s in spans}
    assert relations <= set(TIER2_RELATIONS)
    # The model should recover at least one of the strongly-stated relations.
    assert {"Betrayed", "Serves", "Mentor", "Student"} & relations
