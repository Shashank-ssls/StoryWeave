"""P0 regression: the spoiler fence (KEYSTONE, Phase 5 consolidation).

This is THE permanent regression guard for rule #1 and MUST stay green. It proves all
four fenced surfaces at once: nodes, edges (both-endpoints, incl. Tier-3 identity),
node properties (property + node both-rule), and the serialized projection. Anything
the reader has not been shown at chapter N is invisible.
"""

from __future__ import annotations

from storyweave.db.models import (
    Edge,
    ExtractionMethod,
    Node,
    NodeProperty,
    NodeType,
    RelationTier,
    Work,
)
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


def _edge(
    repo: Repository,
    work_id: int,
    src: int,
    tgt: int,
    revealed: int,
    relation: str = "RelatedTo",
    tier: RelationTier = RelationTier.STRUCTURAL,
) -> int:
    return repo.add_edge(
        Edge(
            work_id=work_id,
            source_id=src,
            target_id=tgt,
            relation=relation,
            tier=tier,
            first_seen_chapter=revealed,
            revealed_chapter=revealed,
            extraction_method=ExtractionMethod.RULE,
        )
    )


def _prop(repo: Repository, node_id: int, key: str, value: str, revealed: int) -> int:
    return repo.add_node_property(
        NodeProperty(
            node_id=node_id,
            key=key,
            value=value,
            first_seen_chapter=revealed,
            revealed_chapter=revealed,
            extraction_method=ExtractionMethod.LLM,
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


# --- property-level reveal (the property both-rule) ------------------------- #


def test_property_revealed_later_than_node() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        wren = _node(repo, wid, "Wren", revealed=1)
        _prop(repo, wren, "rank", "Seer", revealed=5)  # secret stat, reader learns ch5

        assert fence.visible_node_properties(repo, wid, 3) == []
        revealed = fence.visible_node_properties(repo, wid, 5)
        assert len(revealed) == 1 and revealed[0].value == "Seer"

        # And it surfaces on the node in the serialized graph only at/after ch5.
        assert graph_json(repo, wid, 3)["elements"]["nodes"][0]["data"]["properties"] == {}
        assert graph_json(repo, wid, 5)["elements"]["nodes"][0]["data"]["properties"] == {
            "rank": "Seer"
        }


def test_property_of_hidden_node_stays_hidden() -> None:
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        late = _node(repo, wid, "Prince Caelum", revealed=5)
        # Property's own reveal is early, but its node is not revealed until ch5.
        _prop(repo, late, "title", "Heir", revealed=1)

        assert fence.visible_node_properties(repo, wid, 3) == []  # node hidden -> prop hidden
        assert len(fence.visible_node_properties(repo, wid, 5)) == 1


# --- Tier-3 identity reveal (the showcase) --------------------------------- #


def test_identity_edge_is_fenced_like_any_edge() -> None:
    """Wren == Prince Caelum: a SECRET_IDENTITY edge revealed at ch2."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        wren = _node(repo, wid, "Wren", revealed=1)
        caelum = _node(repo, wid, "Prince Caelum", revealed=2)
        _edge(repo, wid, wren, caelum, revealed=2,
              relation="SECRET_IDENTITY", tier=RelationTier.IDENTITY)

        # Before the reveal: only Wren, no identity link.
        assert {n.id for n in fence.visible_nodes(repo, wid, 1)} == {wren}
        assert fence.visible_edges(repo, wid, 1) == []

        # At the reveal chapter: both nodes + the identity edge appear.
        assert {n.id for n in fence.visible_nodes(repo, wid, 2)} == {wren, caelum}
        edges = fence.visible_edges(repo, wid, 2)
        assert len(edges) == 1
        assert edges[0].relation == "SECRET_IDENTITY"
        assert edges[0].tier is RelationTier.IDENTITY


# --- provably no unfenced element in the projection ------------------------ #


def test_projection_never_contains_an_element_past_n() -> None:
    """A mixed graph: at every N, nothing in the projection has revealed_chapter > N."""
    with Repository(":memory:") as repo:
        repo.initialize_schema()
        wid = repo.create_work(Work(slug="t", title="T"))
        a = _node(repo, wid, "A", revealed=1)
        b = _node(repo, wid, "B", revealed=2)
        c = _node(repo, wid, "C", revealed=4)
        _edge(repo, wid, a, b, revealed=2)
        _edge(repo, wid, b, c, revealed=4)
        _prop(repo, a, "k", "v", revealed=3)

        for n in range(0, 6):
            payload = graph_json(repo, wid, n)
            for nd in payload["elements"]["nodes"]:
                assert nd["data"]["revealed_chapter"] <= n
            for e in payload["elements"]["edges"]:
                assert e["data"]["revealed_chapter"] <= n
            # Revealed-only properties: count visible props never exceeds the fence's.
            visible_props = fence.visible_node_properties(repo, wid, n)
            assert all(p.revealed_chapter <= n for p in visible_props)
