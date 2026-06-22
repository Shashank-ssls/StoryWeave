"""The spoiler-fence query layer — the single enforcement chokepoint.

Rule #1: the graph models what the reader has been told by chapter N, not
world-truth. Everything visible to a client passes through here. Two invariants:

* **Node visibility** keys on ``revealed_chapter`` (``revealed_chapter <= N``).
* **Edge visibility** additionally requires BOTH endpoints to be revealed — an edge
  to a not-yet-revealed node is itself invisible (the both-endpoints rule).

Filtering happens at the SQL level (see ``repository.list_*_revealed``); this module
is the sole sanctioned caller of those queries and never post-filters in Python.
Phase 5 consolidates all fencing (graph + search) here; Phase 3 establishes it for
the graph.
"""

from __future__ import annotations

from storyweave.db.models import Edge, Node
from storyweave.db.repository import Repository


def visible_nodes(repo: Repository, work_id: int, chapter: int) -> list[Node]:
    """Nodes the reader may see at chapter N."""
    return repo.list_nodes_revealed(work_id, chapter)


def visible_edges(repo: Repository, work_id: int, chapter: int) -> list[Edge]:
    """Edges the reader may see at chapter N (both endpoints revealed)."""
    return repo.list_edges_revealed(work_id, chapter)
