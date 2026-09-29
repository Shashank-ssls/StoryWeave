"""Graph projection: SQLite -> fenced rows -> Cytoscape JSON.

The fence is applied here via ``query/fence.py`` (the sole sanctioned caller of the
revealed-chapter SQL), so the projected graph only ever contains what the reader may
see at N -- including the both-endpoints rule for edges. Output is valid Cytoscape.js
``elements`` JSON carrying type, subtype, and reveal stamps for the frontend (Phase 8).

Retrofit R3: node selection goes through ``fence.visible_graph_nodes``, which fences
first and then narrows to the four drawable types, so Ability/Concept/Event/Title rows in
a legacy database are never served even though they still load. Each node also carries
its fenced display name and the labels the reader has been given so far.

Retrofit R4 -- defects D1 and D2. The payload used to be projected through an
``nx.DiGraph``, which can hold at most ONE edge per ordered pair. Every extra fenced row
on that pair was silently overwritten: 10 rows at chapter 40 in the v1 baseline, and
after R1 the single survivor of that collapse was a ``SECRET_IDENTITY`` reveal being
relabelled ``REINCARNATION`` (edge 1325, pair 14 -> 150). A projection layer that can
destroy an identity reveal is not a projection layer. The payload is now built
**directly from the fenced rows**: one payload edge per row, no intermediate graph, so
edge count out == fenced row count in, by construction rather than by luck.

``build_graph`` still exists and still returns a NetworkX graph, because analysis code
(metrics, salience) legitimately wants one -- but it is no longer on the serving path,
and it now returns a ``MultiDiGraph`` so that even that caller stops losing rows.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from storyweave.db.models import Edge, Node
from storyweave.db.repository import Repository
from storyweave.query import fence


def _node_payload(
    node: Node,
    display_names: dict[int, str],
    labels_by_node: dict[int, list[dict[str, object]]],
    props_by_node: dict[int | None, dict[str, str]],
) -> dict[str, Any]:
    """One node's payload attributes. Shared by the row path and the NetworkX path."""
    return {
        # Fall back to node.name only when the work has no labels at all (a legacy
        # database predating R3): never invent a name, and never show one the fence
        # has not released.
        "label": display_names.get(node.id or 0, node.name),
        "labels": labels_by_node.get(node.id or 0, []),
        "type": node.type.value,
        "subtype": node.subtype,
        "importance": node.importance,
        "first_seen_chapter": node.first_seen_chapter,
        "revealed_chapter": node.revealed_chapter,
        "extraction_method": node.extraction_method.value,
        "evidence_span": node.evidence_span,
        "properties": props_by_node.get(node.id, {}),
    }


def _edge_payload(edge: Edge) -> dict[str, Any]:
    """One edge's payload attributes, straight off the row.

    ``relation`` comes from the row and nothing downstream may rewrite it -- that is the
    D2 guarantee in one line.
    """
    return {
        "relation": edge.relation,
        "tier": int(edge.tier),
        "first_seen_chapter": edge.first_seen_chapter,
        "revealed_chapter": edge.revealed_chapter,
        "extraction_method": edge.extraction_method.value,
        "evidence_span": edge.evidence_span,
        # Retrofit R4. None on a pre-R4 database, which is honest: those rows have no
        # citation and no grade, and the frontend must not pretend otherwise.
        "weight": edge.weight,
        "grade": edge.grade.value if edge.grade is not None else None,
        "quote": edge.quote,
        "quote_chapter": edge.quote_chapter,
        "kin_role": edge.kin_role,
        "subtype": edge.subtype,
    }


def _fenced_elements(
    repo: Repository, work_id: int, chapter: int
) -> tuple[list[Node], list[Edge], dict[str, Any]]:
    """The fenced nodes, the fenced drawable edges, and the shared node attributes.

    An edge whose endpoint is not DRAWN is dropped here, not later. This narrows the
    payload and can never widen it: the fence has already decided what is VISIBLE; this
    only decides what is DRAWN (retrofit rule 1 keeps the two separate).
    """
    props_by_node: dict[int | None, dict[str, str]] = {}
    for prop in fence.visible_node_properties(repo, work_id, chapter):
        props_by_node.setdefault(prop.node_id, {})[prop.key] = prop.value

    display_names = fence.visible_display_names(repo, work_id, chapter)
    labels_by_node: dict[int, list[dict[str, object]]] = {}
    for lab in fence.visible_entity_labels(repo, work_id, chapter):
        labels_by_node.setdefault(lab.entity_id, []).append(
            {
                "label": lab.label,
                "kind": lab.kind.value,
                "revealed_chapter": lab.revealed_chapter,
                "is_primary": lab.is_primary,
                "quote": lab.quote,
            }
        )

    nodes = fence.visible_graph_nodes(repo, work_id, chapter)
    drawn = {node.id for node in nodes}
    edges = [
        edge
        for edge in fence.visible_edges(repo, work_id, chapter)
        if edge.source_id in drawn and edge.target_id in drawn
    ]
    shared = {
        "display_names": display_names,
        "labels_by_node": labels_by_node,
        "props_by_node": props_by_node,
    }
    return nodes, edges, shared


def build_graph(repo: Repository, work_id: int, chapter: int) -> nx.MultiDiGraph:
    """A fenced NetworkX view of the work at chapter N, for ANALYSIS (not serving).

    ``MultiDiGraph``, not ``DiGraph``: two different relations between the same pair are
    two different facts, and a simple digraph silently keeps only the last one (D1/D2).
    """
    nodes, edges, shared = _fenced_elements(repo, work_id, chapter)
    graph: nx.MultiDiGraph = nx.MultiDiGraph()
    for node in nodes:
        graph.add_node(node.id, **_node_payload(node, **shared))
    for edge in edges:
        graph.add_edge(edge.source_id, edge.target_id, key=edge.id, id=edge.id,
                       **_edge_payload(edge))
    return graph


def to_cytoscape(graph: nx.DiGraph | nx.MultiDiGraph) -> dict[str, Any]:
    """Serialize a NetworkX graph to Cytoscape.js ``elements`` JSON.

    Kept for callers that already hold a graph. The serving path uses
    :func:`graph_json`, which never builds one.
    """
    nodes = [
        {"data": {"id": str(node_id), **attrs}} for node_id, attrs in graph.nodes(data=True)
    ]
    edges = [
        {
            "data": {
                "id": f"e{attrs.get('id')}",
                "source": str(source),
                "target": str(target),
                **{k: v for k, v in attrs.items() if k != "id"},
            }
        }
        for source, target, attrs in graph.edges(data=True)
    ]
    return {"elements": {"nodes": nodes, "edges": edges}}


def graph_json(repo: Repository, work_id: int, chapter: int) -> dict[str, Any]:
    """The fenced Cytoscape payload at chapter N, built straight from the rows.

    One fenced, drawable row in -> exactly one payload edge out. No intermediate graph
    object exists to collapse anything (defects D1 and D2).
    """
    nodes, edges, shared = _fenced_elements(repo, work_id, chapter)
    return {
        "elements": {
            "nodes": [
                {"data": {"id": str(node.id), **_node_payload(node, **shared)}}
                for node in nodes
            ],
            "edges": [
                {
                    "data": {
                        "id": f"e{edge.id}",
                        "source": str(edge.source_id),
                        "target": str(edge.target_id),
                        **_edge_payload(edge),
                    }
                }
                for edge in edges
            ],
        }
    }
