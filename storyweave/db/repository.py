"""The one and only SQL audit point (CLAUDE.md architecture rule).

Every SQL statement in StoryWeave lives here. SQLite is the source of truth; the
graph projection and vector index are derived and rebuildable from this database.

The schema encodes the full 8-type ontology from day one (SPEC §5): nodes with a
nullable subtype, three-tier edges, and a node-property mechanism — each carrying
the universal reveal stamps ``first_seen_chapter`` + ``revealed_chapter``.
Phase 0 only creates the schema and exposes minimal primitives; extraction logic
arrives in later phases.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType

from storyweave.db.models import (
    ALL_RELATIONS,
    Edge,
    Node,
    NodeProperty,
    NodeType,
    RelationTier,
    Work,
)

# Controlled-vocabulary fragments for CHECK constraints, derived from the ontology
# so the SQL and the pydantic mirrors can never drift.
_NODE_TYPE_LIST = ", ".join(f"'{t.value}'" for t in NodeType)
_RELATION_LIST = ", ".join(f"'{r}'" for r in ALL_RELATIONS)
_TIER_LIST = ", ".join(str(t.value) for t in RelationTier)

SCHEMA: str = f"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS works (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL
);

-- Nodes: the eight ontology types, a nullable subtype, and the universal reveal
-- stamps. Provenance (extraction_method + evidence_span) on every row.
CREATE TABLE IF NOT EXISTS nodes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id             INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    type                TEXT NOT NULL CHECK (type IN ({_NODE_TYPE_LIST})),
    name                TEXT NOT NULL,
    subtype             TEXT,
    importance          REAL NOT NULL DEFAULT 0.0,
    first_seen_chapter  INTEGER NOT NULL,
    revealed_chapter    INTEGER NOT NULL,
    extraction_method   TEXT NOT NULL CHECK (extraction_method IN ('gliner', 'rule', 'llm')),
    evidence_span       TEXT
);

-- Edges: three-tier typed relationships. An edge is visible at chapter N only if
-- BOTH endpoints are visible (enforced later in query/fence.py).
CREATE TABLE IF NOT EXISTS edges (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id             INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    source_id           INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id           INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation            TEXT NOT NULL CHECK (relation IN ({_RELATION_LIST})),
    tier                INTEGER NOT NULL CHECK (tier IN ({_TIER_LIST})),
    first_seen_chapter  INTEGER NOT NULL,
    revealed_chapter    INTEGER NOT NULL,
    extraction_method   TEXT NOT NULL CHECK (extraction_method IN ('gliner', 'rule', 'llm')),
    evidence_span       TEXT
);

-- Node properties: reveal-stamped facts about a node (the property-level fence).
CREATE TABLE IF NOT EXISTS node_properties (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id             INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    key                 TEXT NOT NULL,
    value               TEXT NOT NULL,
    first_seen_chapter  INTEGER NOT NULL,
    revealed_chapter    INTEGER NOT NULL,
    extraction_method   TEXT NOT NULL CHECK (extraction_method IN ('gliner', 'rule', 'llm')),
    evidence_span       TEXT
);

CREATE INDEX IF NOT EXISTS idx_nodes_work        ON nodes(work_id);
CREATE INDEX IF NOT EXISTS idx_nodes_revealed    ON nodes(revealed_chapter);
CREATE INDEX IF NOT EXISTS idx_edges_work        ON edges(work_id);
CREATE INDEX IF NOT EXISTS idx_edges_revealed    ON edges(revealed_chapter);
CREATE INDEX IF NOT EXISTS idx_edges_endpoints   ON edges(source_id, target_id);
CREATE INDEX IF NOT EXISTS idx_props_node        ON node_properties(node_id);
CREATE INDEX IF NOT EXISTS idx_props_revealed    ON node_properties(revealed_chapter);
"""


class Repository:
    """Thin, fully-typed wrapper over the SQLite connection. The sole SQL surface."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self._db_path = db_path
        path_arg = str(db_path)
        if path_arg != ":memory:":
            Path(path_arg).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path_arg)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    # --- lifecycle ------------------------------------------------------- #

    def initialize_schema(self) -> None:
        """Create the full 8-type schema if it does not yet exist (idempotent)."""
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Repository:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- works ----------------------------------------------------------- #

    def create_work(self, work: Work) -> int:
        cur = self.conn.execute(
            "INSERT INTO works (slug, title) VALUES (?, ?)",
            (work.slug, work.title),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def get_work(self, work_id: int) -> Work | None:
        row = self.conn.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()
        return Work(**dict(row)) if row else None

    # --- nodes ----------------------------------------------------------- #

    def add_node(self, node: Node) -> int:
        cur = self.conn.execute(
            """INSERT INTO nodes
                 (work_id, type, name, subtype, importance,
                  first_seen_chapter, revealed_chapter, extraction_method, evidence_span)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.work_id,
                node.type.value,
                node.name,
                node.subtype,
                node.importance,
                node.first_seen_chapter,
                node.revealed_chapter,
                node.extraction_method.value,
                node.evidence_span,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    # --- edges ----------------------------------------------------------- #

    def add_edge(self, edge: Edge) -> int:
        cur = self.conn.execute(
            """INSERT INTO edges
                 (work_id, source_id, target_id, relation, tier,
                  first_seen_chapter, revealed_chapter, extraction_method, evidence_span)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.work_id,
                edge.source_id,
                edge.target_id,
                edge.relation,
                edge.tier.value,
                edge.first_seen_chapter,
                edge.revealed_chapter,
                edge.extraction_method.value,
                edge.evidence_span,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    # --- node properties ------------------------------------------------- #

    def add_node_property(self, prop: NodeProperty) -> int:
        cur = self.conn.execute(
            """INSERT INTO node_properties
                 (node_id, key, value,
                  first_seen_chapter, revealed_chapter, extraction_method, evidence_span)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                prop.node_id,
                prop.key,
                prop.value,
                prop.first_seen_chapter,
                prop.revealed_chapter,
                prop.extraction_method.value,
                prop.evidence_span,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)
