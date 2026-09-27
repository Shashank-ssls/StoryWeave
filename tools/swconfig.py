"""Shared definitions for the measurement harness (tools/).

This module is the harness's single description of WHAT each measured configuration
filters. Both the metrics script and the report generator read it, so the numbers and
the "Measurement conditions" prose can never drift apart.

Two configurations are measured. They are NOT two versions of the app — they are two
points in the SAME codebase's one pipeline, measured against the same database:

* ``api_payload``   — exactly what ``GET /works/{slug}/graph`` sends: the spoiler fence
  and nothing else. Produced here by calling the real ``query/fence.py`` through the
  real ``db/repository.py``, never by re-writing its SQL.

* ``rendered_view`` — that payload after the frontend's own client-side filters, i.e.
  what the Stemma canvas actually draws. Mirrored from the TypeScript source:
  ``frontend/src/graph/viewModel.ts`` (``buildViewModel``) then
  ``frontend/src/graph/stemmaModel.ts`` (``visibleGraph``, cast = "principal").

There is no salience ranking and no disparity/backbone filter anywhere in this
codebase; ``rendered_view`` is the real cast-reduction rule that does exist.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from storyweave.db.repository import Repository

# --- configuration identities ------------------------------------------------ #

API_PAYLOAD = "api_payload"
RENDERED_VIEW = "rendered_view"
RENDERED_EVERYONE = "rendered_everyone"
CONFIGS: tuple[str, ...] = (API_PAYLOAD, RENDERED_VIEW, RENDERED_EVERYONE)

#: Which configurations have a view the app can actually draw, and the cast-toggle state
#: that produces them. `api_payload` is deliberately absent: the app has NO view that draws
#: the unfiltered payload, so it is measured in the CSV but never screenshotted.
RENDERABLE_CAST: dict[str, str] = {
    RENDERED_VIEW: "principal",
    RENDERED_EVERYONE: "everyone",
}

#: Human-readable statement of the active filters, quoted verbatim into REPORT.md.
FILTER_DESCRIPTIONS: dict[str, str] = {
    API_PAYLOAD: (
        "Spoiler fence only. `query/fence.py` -> `repository.list_nodes_revealed` "
        "(`revealed_chapter <= N`) and `repository.list_edges_revealed` (edge AND both "
        "endpoints revealed, enforced in SQL). No other filter is applied; this is the "
        "payload the API sends to the client."
    ),
    RENDERED_VIEW: (
        "Spoiler fence, then the frontend's client-side view filters as drawn by the "
        "Stemma: (1) `buildViewModel` drops Concept/Event nodes to 'Also mentioned' and "
        "drops Title/unknown types entirely; (2) it drops any identity edge with no "
        "`evidence_span` (the R8 citation gate); (3) it merges parallel edges on the "
        "unordered node pair, an identity edge absorbing a social/structural one; "
        "(4) `visibleGraph` with cast='principal' keeps a node only when "
        "degree >= 2 OR it touches an identity edge OR it is the focus; (5) edges are "
        "then kept only when both endpoints survived."
    ),
    RENDERED_EVERYONE: (
        "Spoiler fence, then the same `buildViewModel` stage as `rendered_view` -- "
        "Concept/Event dropped to 'Also mentioned', Title/unknown dropped, uncited "
        "identity edges dropped, parallel edges merged on the unordered pair -- but "
        "`visibleGraph` with cast='everyone', which applies NO degree or identity "
        "cast-reduction: every drawable node is kept. This is the widest view the app can "
        "actually render, and the screenshot counterpart of `api_payload`."
    ),
}

# --- the frontend's ontology constants, mirrored ----------------------------- #

# frontend/src/ontology.ts IDENTITY_RELATIONS
IDENTITY_RELATIONS: frozenset[str] = frozenset(
    {"SAME_AS", "ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"}
)

# frontend/src/graph/viewModel.ts STRUCTURAL
STRUCTURAL_RELATIONS: frozenset[str] = frozenset(
    {"LocatedIn", "MemberOf", "AffiliatedWith", "LeaderOf"}
)

# frontend/src/graph/viewModel.ts kindOf(): node type -> canvas kind.
# Concept/Event -> "Also mentioned" (not drawn); Title/unknown -> never a node.
NODE_KIND: dict[str, str | None] = {
    "Character": "person",
    "Organization": "order",
    "Place": "place",
    "Item": "thing",
    "Ability": "thing",
    "Concept": None,
    "Event": None,
    "Title": None,
}

#: cast='principal' threshold from stemmaModel.ts visibleGraph().
PRINCIPAL_MIN_DEGREE = 2

# --- database access --------------------------------------------------------- #


def open_readonly(db_path: str | Path) -> Repository:
    """A ``Repository`` bound to a strictly read-only connection.

    The harness must never be able to write to a database it is measuring. ``Repository``
    itself opens read-write (and would ``mkdir`` the parent), so the repo is constructed
    against ``:memory:`` -- touching no file -- and its connection is then replaced with a
    ``mode=ro`` URI connection. All the real fenced SQL in ``db/repository.py`` is reused
    unchanged; only the connection's writability differs.
    """
    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"database not found: {path}")
    repo = Repository(":memory:")
    repo.conn.close()
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    repo.conn = conn
    return repo
