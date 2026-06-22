"""The spoiler-fence query layer — the single enforcement chokepoint (KEYSTONE).

Rule #1: the graph models what the reader has been told by chapter N, not
world-truth. Everything a client can see passes through here. The fence keys on
``revealed_chapter`` and enforces four consolidated invariants:

* **Nodes** — visible when ``revealed_chapter <= N``.
* **Edges** — visible when the edge AND BOTH endpoints are revealed (the
  both-endpoints rule). This covers Tier-3 IDENTITY edges (SAME_AS, ALIAS,
  SECRET_IDENTITY, REINCARNATION, TRANSMIGRATED_INTO) for free: an identity reveal
  is just an edge whose ``revealed_chapter`` is the chapter the reader learns it
  (e.g. Wren == Prince Caelum revealed at ch2; Zhou Mingrui ⇄ Klein at ch1).
* **Node properties** — visible when the property AND its node are revealed (the
  property-level both-rule), so a secret stat on a hidden character stays hidden.
* **Search hits** — visible when ``chapter_ordinal <= N`` (chunk reveal key).

Enforcement lives at the data layer: SQL ``WHERE``/``JOIN`` clauses in
``repository.list_*_revealed`` and the metadata filter inside the vector store's
``query``. This module is the ONLY sanctioned caller of those filtered reads; it
never post-filters in Python and there is no unfenced read path exposed to callers
(graph projection and search both route through here). Phases 3–4 established the
graph and search fences; Phase 5 consolidates them and adds property + identity
coverage, guarded by the permanent P0 regression in ``tests/test_fence.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from storyweave.db.models import Edge, Node, NodeProperty
from storyweave.db.repository import Repository

if TYPE_CHECKING:  # pragma: no cover - typing only (avoids a runtime import cycle)
    from storyweave.search.store import BaseVectorStore, SearchHit


def visible_nodes(repo: Repository, work_id: int, chapter: int) -> list[Node]:
    """Nodes the reader may see at chapter N."""
    return repo.list_nodes_revealed(work_id, chapter)


def visible_edges(repo: Repository, work_id: int, chapter: int) -> list[Edge]:
    """Edges the reader may see at chapter N (edge + both endpoints revealed).

    Tier-3 identity edges are fenced by exactly this rule — no special-casing.
    """
    return repo.list_edges_revealed(work_id, chapter)


def visible_node_properties(
    repo: Repository, work_id: int, chapter: int
) -> list[NodeProperty]:
    """Node properties the reader may see at chapter N (property + node revealed)."""
    return repo.list_node_properties_revealed(work_id, chapter)


def visible_chunk_hits(
    store: BaseVectorStore,
    query_embedding: list[float],
    work_id: int,
    chapter: int,
    top_k: int,
) -> list[SearchHit]:
    """Fenced vector retrieval: the sanctioned entry to the index.

    Guarantees the chapter constraint is passed so the store filters
    ``chapter_ordinal <= chapter`` at the index level — results are already fenced
    when they reach the caller; nothing is post-filtered afterwards.
    """
    return store.query(query_embedding, work_id=work_id, top_k=top_k, max_chapter=chapter)
