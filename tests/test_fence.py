"""Phase 3 (P0 regression): the spoiler fence and the both-endpoints rule.

This is a permanent regression guard for rule #1. It MUST stay green: a node/edge
that the reader has not yet been shown at chapter N is invisible, and an edge to a
not-yet-revealed node is itself invisible even if the edge's own reveal is early.
"""

from __future__ import annotations

from storyweave.db.models import Edge, ExtractionMethod, Node, NodeType, RelationTier, Work
from storyweave.db.repository import Repository
from storyweave.graph.serialize import graph_json
from storyweave.query import fence


def _node(repo: Repository, work_id: int, name: str, revealed: int) -> int:
    return repo.add_node(
        Node(
            work_id=work_id,
            type=NodeType.CHARACTER,
            name=name,
            first_seen_chapter=revealed,
            revealed_chapter=revealed,
            extraction_method=ExtractionMethod.GLINER,
        )
    )


def _edge(repo: Repository, work_id: int, src: int, tgt: int, revealed: int) -> int:
    return repo.add_edge(
        Edge(
            work_id=work_id,
            source_id=src,
            target_id=tgt,
            relation="RelatedTo",
            tier=RelationTier.STRUCTURAL,
            first_seen_chapter=revealed,
            revealed_chapter=revealed,
            extraction_method=ExtractionMethod.RULE,
        )
    )


def test_both_endpoints_rule_hides_edge_to_unrevealed_node() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        early = _node(repo, wid, "Wren", revealed=1)
        late = _node(repo, wid, "Prince Caelum", revealed=5)
        # Edge is itself "revealed" at ch1, but its target isn't revealed until ch5.
        _edge(repo, wid, early, late, revealed=1)

        # At N=3: late node hidden, so the edge is hidden too (both-endpoints rule).
        assert {n.id for n in fence.visible_nodes(repo, wid, 3)} == {early}
        assert fence.visible_edges(repo, wid, 3) == []

        # At N=5: both endpoints revealed -> node and edge appear.
        assert {n.id for n in fence.visible_nodes(repo, wid, 5)} == {early, late}
        assert len(fence.visible_edges(repo, wid, 5)) == 1


def test_edge_level_reveal_is_independent_of_endpoints() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        a = _node(repo, wid, "A", revealed=1)
        b = _node(repo, wid, "B", revealed=1)
        # Both endpoints visible early, but the relationship itself is a ch5 reveal.
        _edge(repo, wid, a, b, revealed=5)

        assert len(fence.visible_nodes(repo, wid, 3)) == 2
        assert fence.visible_edges(repo, wid, 3) == []  # edge hidden until its own reveal
        assert len(fence.visible_edges(repo, wid, 5)) == 1


def test_serialized_graph_is_fenced() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        early = _node(repo, wid, "Wren", revealed=1)
        late = _node(repo, wid, "Prince Caelum", revealed=5)
        _edge(repo, wid, early, late, revealed=1)

        low = graph_json(repo, wid, 3)
        assert len(low["elements"]["nodes"]) == 1
        assert low["elements"]["edges"] == []

        high = graph_json(repo, wid, 5)
        assert len(high["elements"]["nodes"]) == 2
        assert len(high["elements"]["edges"]) == 1
        # Cytoscape shape: edge data carries string source/target + relation.
        edge_data = high["elements"]["edges"][0]["data"]
        assert edge_data["source"] == str(early) and edge_data["target"] == str(late)
        assert edge_data["relation"] == "RelatedTo"
