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
    Chapter,
    Chunk,
    Edge,
    Mention,
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

-- Source-data layer (Phase 1): the raw ingested text. Not graph elements, so no
-- reveal stamps. content_hash drives idempotent re-ingest.
CREATE TABLE IF NOT EXISTS chapters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id       INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    ordinal       INTEGER NOT NULL,
    title         TEXT,
    clean_text    TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    source_path   TEXT,
    UNIQUE (work_id, ordinal)
);

CREATE TABLE IF NOT EXISTS chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id    INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    work_id       INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    ordinal       INTEGER NOT NULL,
    char_start    INTEGER NOT NULL,
    char_end      INTEGER NOT NULL,
    text          TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    UNIQUE (chapter_id, ordinal)
);

-- Raw GLiNER candidate mentions (Phase 2), persisted before clustering. Offsets
-- index into the chapter's clean_text. node_id is backfilled after clustering.
CREATE TABLE IF NOT EXISTS mentions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id           INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    chapter_id        INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    chapter_ordinal   INTEGER NOT NULL,
    ordinal           INTEGER NOT NULL,
    surface           TEXT NOT NULL,
    type              TEXT NOT NULL CHECK (type IN ({_NODE_TYPE_LIST})),
    subtype           TEXT,
    char_start        INTEGER NOT NULL,
    char_end          INTEGER NOT NULL,
    score             REAL NOT NULL,
    extraction_method TEXT NOT NULL CHECK (extraction_method IN ('gliner', 'rule', 'llm')),
    node_id           INTEGER REFERENCES nodes(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_work        ON nodes(work_id);
CREATE INDEX IF NOT EXISTS idx_nodes_revealed    ON nodes(revealed_chapter);
CREATE INDEX IF NOT EXISTS idx_edges_work        ON edges(work_id);
CREATE INDEX IF NOT EXISTS idx_edges_revealed    ON edges(revealed_chapter);
CREATE INDEX IF NOT EXISTS idx_edges_endpoints   ON edges(source_id, target_id);
CREATE INDEX IF NOT EXISTS idx_props_node        ON node_properties(node_id);
CREATE INDEX IF NOT EXISTS idx_props_revealed    ON node_properties(revealed_chapter);
CREATE INDEX IF NOT EXISTS idx_chapters_work     ON chapters(work_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chapter    ON chunks(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chunks_work       ON chunks(work_id);
CREATE INDEX IF NOT EXISTS idx_mentions_work     ON mentions(work_id);
CREATE INDEX IF NOT EXISTS idx_mentions_chapter  ON mentions(chapter_id);
CREATE INDEX IF NOT EXISTS idx_mentions_node     ON mentions(node_id);
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

    def get_work_by_slug(self, slug: str) -> Work | None:
        row = self.conn.execute("SELECT * FROM works WHERE slug = ?", (slug,)).fetchone()
        return Work(**dict(row)) if row else None

    def get_or_create_work(self, slug: str, title: str) -> int:
        existing = self.get_work_by_slug(slug)
        if existing is not None and existing.id is not None:
            return existing.id
        return self.create_work(Work(slug=slug, title=title))

    # --- chapters (Phase 1) ---------------------------------------------- #

    def get_chapter_by_ordinal(self, work_id: int, ordinal: int) -> Chapter | None:
        row = self.conn.execute(
            "SELECT * FROM chapters WHERE work_id = ? AND ordinal = ?",
            (work_id, ordinal),
        ).fetchone()
        return Chapter(**dict(row)) if row else None

    def add_chapter(self, chapter: Chapter) -> int:
        cur = self.conn.execute(
            """INSERT INTO chapters
                 (work_id, ordinal, title, clean_text, content_hash, source_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                chapter.work_id,
                chapter.ordinal,
                chapter.title,
                chapter.clean_text,
                chapter.content_hash,
                chapter.source_path,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def delete_chapter(self, chapter_id: int) -> None:
        """Delete a chapter; its chunks cascade away (used on content change)."""
        self.conn.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
        self.conn.commit()

    def list_chapters(self, work_id: int) -> list[Chapter]:
        rows = self.conn.execute(
            "SELECT * FROM chapters WHERE work_id = ? ORDER BY ordinal",
            (work_id,),
        ).fetchall()
        return [Chapter(**dict(r)) for r in rows]

    def count_chapters(self, work_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM chapters WHERE work_id = ?", (work_id,)
        ).fetchone()
        return int(row["n"])

    # --- chunks (Phase 1) ------------------------------------------------- #

    def add_chunk(self, chunk: Chunk) -> int:
        cur = self.conn.execute(
            """INSERT INTO chunks
                 (chapter_id, work_id, ordinal, char_start, char_end, text, content_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                chunk.chapter_id,
                chunk.work_id,
                chunk.ordinal,
                chunk.char_start,
                chunk.char_end,
                chunk.text,
                chunk.content_hash,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def list_chunks(self, chapter_id: int) -> list[Chunk]:
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE chapter_id = ? ORDER BY ordinal",
            (chapter_id,),
        ).fetchall()
        return [Chunk(**dict(r)) for r in rows]

    def list_chunks_for_work(self, work_id: int) -> list[Chunk]:
        """All chunks of a work (for rebuilding the vector index from SQLite)."""
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE work_id = ? ORDER BY id", (work_id,)
        ).fetchall()
        return [Chunk(**dict(r)) for r in rows]

    def count_chunks(self, work_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM chunks WHERE work_id = ?", (work_id,)
        ).fetchone()
        return int(row["n"])

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

    def list_nodes(self, work_id: int) -> list[Node]:
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE work_id = ? ORDER BY id", (work_id,)
        ).fetchall()
        return [Node(**dict(r)) for r in rows]

    def count_nodes(self, work_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM nodes WHERE work_id = ?", (work_id,)
        ).fetchone()
        return int(row["n"])

    def clear_nodes(self, work_id: int) -> None:
        """Drop all nodes for a work (extraction is derived + idempotently rebuilt)."""
        self.conn.execute("DELETE FROM nodes WHERE work_id = ?", (work_id,))
        self.conn.commit()

    # --- mentions (Phase 2) ---------------------------------------------- #

    def add_mention(self, mention: Mention) -> int:
        cur = self.conn.execute(
            """INSERT INTO mentions
                 (work_id, chapter_id, chapter_ordinal, ordinal, surface, type, subtype,
                  char_start, char_end, score, extraction_method, node_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mention.work_id,
                mention.chapter_id,
                mention.chapter_ordinal,
                mention.ordinal,
                mention.surface,
                mention.type.value,
                mention.subtype,
                mention.char_start,
                mention.char_end,
                mention.score,
                mention.extraction_method.value,
                mention.node_id,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def list_mentions(self, work_id: int) -> list[Mention]:
        rows = self.conn.execute(
            "SELECT * FROM mentions WHERE work_id = ? ORDER BY id", (work_id,)
        ).fetchall()
        return [Mention(**dict(r)) for r in rows]

    def count_mentions(self, work_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM mentions WHERE work_id = ?", (work_id,)
        ).fetchone()
        return int(row["n"])

    def clear_mentions(self, work_id: int) -> None:
        self.conn.execute("DELETE FROM mentions WHERE work_id = ?", (work_id,))
        self.conn.commit()

    def set_mention_node(self, mention_id: int, node_id: int) -> None:
        self.conn.execute(
            "UPDATE mentions SET node_id = ? WHERE id = ?", (node_id, mention_id)
        )
        self.conn.commit()

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

    def list_edges(self, work_id: int) -> list[Edge]:
        rows = self.conn.execute(
            "SELECT * FROM edges WHERE work_id = ? ORDER BY id", (work_id,)
        ).fetchall()
        return [Edge(**dict(r)) for r in rows]

    def count_edges(self, work_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM edges WHERE work_id = ?", (work_id,)
        ).fetchone()
        return int(row["n"])

    def clear_edges(self, work_id: int) -> None:
        """Drop all edges for a work (relations are derived + idempotently rebuilt)."""
        self.conn.execute("DELETE FROM edges WHERE work_id = ?", (work_id,))
        self.conn.commit()

    # --- fenced reads (the spoiler fence enforced at the SQL level) ------- #
    # These are the SANCTIONED queries that query/fence.py wraps. Visibility keys on
    # revealed_chapter; edges additionally require BOTH endpoints to be revealed.

    def list_nodes_revealed(self, work_id: int, chapter: int) -> list[Node]:
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE work_id = ? AND revealed_chapter <= ? ORDER BY id",
            (work_id, chapter),
        ).fetchall()
        return [Node(**dict(r)) for r in rows]

    def list_edges_revealed(self, work_id: int, chapter: int) -> list[Edge]:
        rows = self.conn.execute(
            """SELECT e.*
                 FROM edges e
                 JOIN nodes s ON e.source_id = s.id
                 JOIN nodes t ON e.target_id = t.id
                WHERE e.work_id = ?
                  AND e.revealed_chapter <= ?
                  AND s.revealed_chapter <= ?   -- both-endpoints rule, in SQL
                  AND t.revealed_chapter <= ?
                ORDER BY e.id""",
            (work_id, chapter, chapter, chapter),
        ).fetchall()
        return [Edge(**dict(r)) for r in rows]

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

    def list_node_properties(self, node_id: int) -> list[NodeProperty]:
        rows = self.conn.execute(
            "SELECT * FROM node_properties WHERE node_id = ? ORDER BY id", (node_id,)
        ).fetchall()
        return [NodeProperty(**dict(r)) for r in rows]

    def list_node_properties_revealed(
        self, work_id: int, chapter: int
    ) -> list[NodeProperty]:
        """Properties visible at chapter N: the property AND its node must be revealed.

        The property-level both-rule — a property of a not-yet-revealed node stays
        hidden even if the property's own reveal is early.
        """
        rows = self.conn.execute(
            """SELECT pr.*
                 FROM node_properties pr
                 JOIN nodes n ON pr.node_id = n.id
                WHERE n.work_id = ?
                  AND pr.revealed_chapter <= ?
                  AND n.revealed_chapter <= ?
                ORDER BY pr.id""",
            (work_id, chapter, chapter),
        ).fetchall()
        return [NodeProperty(**dict(r)) for r in rows]
