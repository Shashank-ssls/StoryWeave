"""Graph projection: SQLite -> NetworkX (fenced by chapter N) -> Cytoscape JSON.

The fence is applied here via ``query/fence.py`` (the sole sanctioned caller of the
revealed-chapter SQL), so the projected graph only ever contains what the reader may
see at N — including the both-endpoints rule for edges. Output is valid Cytoscape.js
``elements`` JSON carrying type, subtype, and reveal stamps for the frontend (Phase 8).
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from storyweave.db.repository import Repository
from storyweave.query import fence


def build_graph(repo: Repository, work_id: int, chapter: int) -> nx.DiGraph:
    """Build a fenced NetworkX directed graph of the work at chapter N.

    Nodes, edges, AND node properties are all fenced through ``query/fence.py``.
    """
    # Revealed properties only (property-level both-rule applied in the fence).
    props_by_node: dict[int | None, dict[str, str]] = {}
    for prop in fence.visible_node_properties(repo, work_id, chapter):
        props_by_node.setdefault(prop.node_id, {})[prop.key] = prop.value

    graph: nx.DiGraph = nx.DiGraph()
    for node in fence.visible_nodes(repo, work_id, chapter):
        graph.add_node(
            node.id,
            label=node.name,
            type=node.type.value,
            subtype=node.subtype,
            importance=node.importance,
            first_seen_chapter=node.first_seen_chapter,
            revealed_chapter=node.revealed_chapter,
            extraction_method=node.extraction_method.value,
            evidence_span=node.evidence_span,
            properties=props_by_node.get(node.id, {}),
        )
    for edge in fence.visible_edges(repo, work_id, chapter):
        graph.add_edge(
            edge.source_id,
            edge.target_id,
            id=edge.id,
            relation=edge.relation,
            tier=int(edge.tier),
            first_seen_chapter=edge.first_seen_chapter,
            revealed_chapter=edge.revealed_chapter,
            extraction_method=edge.extraction_method.value,
            evidence_span=edge.evidence_span,
        )
    return graph


def to_cytoscape(graph: nx.DiGraph) -> dict[str, Any]:
    """Serialize a NetworkX graph to Cytoscape.js ``elements`` JSON."""
    nodes = [
        {"data": {"id": str(node_id), **attrs}}
        for node_id, attrs in graph.nodes(data=True)
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
    """Convenience: fenced graph at N as Cytoscape JSON."""
    return to_cytoscape(build_graph(repo, work_id, chapter))
