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
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType

from storyweave.db.models import (
    ALL_RELATIONS,
    GRAPH_NODE_TYPES,
    LEGACY_TYPE_MAP,
    RELATIONS,
    Arc,
    Chapter,
    Chunk,
    Edge,
    EntityLabel,
    ExtractionMethod,
    LabelKind,
    Mention,
    Node,
    NodeProperty,
    NodeSalience,
    NodeType,
    RelationGrade,
    RelationTier,
    Work,
    is_graph_type,
)

# Controlled-vocabulary fragments for CHECK constraints, derived from the ontology
# so the SQL and the pydantic mirrors can never drift.
_NODE_TYPE_LIST = ", ".join(f"'{t.value}'" for t in NodeType)
# The stored relation vocabulary is v1's fifteen-per-tier list PLUS retrofit R4's
# twelve. Both, not one: R4's producer writes the new names, while the frozen v1
# baseline and the Hollow Crown fixture are full of the old ones and must keep loading.
# `LEGACY_RELATION_MAP` in db/models.py is where each old name's fate is recorded.
_STORED_RELATIONS: tuple[str, ...] = (
    *ALL_RELATIONS,
    *(r.value for r in RELATIONS if r.value not in ALL_RELATIONS),
)
_RELATION_LIST = ", ".join(f"'{r}'" for r in _STORED_RELATIONS)
_TIER_LIST = ", ".join(str(t.value) for t in RelationTier)
_METHOD_LIST = ", ".join(f"'{m.value}'" for m in ExtractionMethod)
_GRADE_LIST = ", ".join(f"'{g.value}'" for g in RelationGrade)
_LABEL_KIND_LIST = ", ".join(f"'{k.value}'" for k in LabelKind)
# The graph's four display types (retrofit R3). Used ONLY in the display clause of
# list_graph_nodes_revealed, never in a fence clause - they are different filters with
# different purposes and must stay visibly separate.
_GRAPH_TYPE_LIST = ", ".join(f"'{t.value}'" for t in GRAPH_NODE_TYPES)

# The `edges` DDL as its own constant: `migrate_edges_relation_vocabulary` rebuilds
# the table from this exact statement, so the rebuilt table can never drift from
# the one a fresh database gets.
_EDGES_DDL: str = f"""CREATE TABLE IF NOT EXISTS edges (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id             INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    source_id           INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id           INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation            TEXT NOT NULL CHECK (relation IN ({_RELATION_LIST})),
    tier                INTEGER NOT NULL CHECK (tier IN ({_TIER_LIST})),
    first_seen_chapter  INTEGER NOT NULL,
    revealed_chapter    INTEGER NOT NULL,
    extraction_method   TEXT NOT NULL CHECK (extraction_method IN ({_METHOD_LIST})),
    evidence_span       TEXT,
    -- Retrofit R4. All default, so a pre-R4 row is still a valid Edge. `weight` is what
    -- replaces duplicate rows: repeat evidence increments it and keeps the earliest
    -- quote. `grade` is STATED only when the quote names both participants and a cue.
    weight              INTEGER NOT NULL DEFAULT 1,
    grade               TEXT CHECK (grade IS NULL OR grade IN ({_GRADE_LIST})),
    quote               TEXT,
    quote_chapter       INTEGER,
    kin_role            TEXT,
    surface_term        TEXT,
    subtype             TEXT
);"""

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
    extraction_method   TEXT NOT NULL CHECK (extraction_method IN ({_METHOD_LIST})),
    evidence_span       TEXT
);

-- Edges: three-tier typed relationships. An edge is visible at chapter N only if
-- BOTH endpoints are visible (enforced later in query/fence.py).
{_EDGES_DDL}

-- One row per (work, relation, head, tail) FOR R4 EDGES: R4 has no parallel duplicates
-- of the same relation on the same pair. DIFFERENT relations on the same pair remain
-- separate rows, which is exactly the defect D2 fix - the old nx.DiGraph projection
-- collapsed them.
--
-- PARTIAL, on `grade IS NOT NULL`, and that scope is the honest one rather than a
-- convenience: `grade` is non-NULL exactly on rows this retrofit's validator wrote, and
-- the uniqueness claim is a claim about R4's producer, not about history. Legacy rows
-- predate the key and can legitimately violate it - the Phase-7d coref merge, for one,
-- re-points an edge onto a pair that already carries the same relation at a different
-- tier, and it is right to keep both. A full index would make R4 silently break a
-- working legacy path; this one cannot.
CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_unique_relation
    ON edges(work_id, relation, source_id, target_id) WHERE grade IS NOT NULL;

-- Retrofit R4: every proposal the validator refuses, with its reason code. Rejections
-- are evidence, not silence - the phase reports counts by reason.
CREATE TABLE IF NOT EXISTS validator_rejections (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id           INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    relation          TEXT NOT NULL,
    source_surface    TEXT,
    target_surface    TEXT,
    source_id         INTEGER,
    target_id         INTEGER,
    quote             TEXT,
    quote_chapter     INTEGER,
    reason            TEXT NOT NULL,
    detail            TEXT
);

CREATE INDEX IF NOT EXISTS idx_rejections_work ON validator_rejections(work_id, reason);

-- Node properties: reveal-stamped facts about a node (the property-level fence).
CREATE TABLE IF NOT EXISTS node_properties (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id             INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    key                 TEXT NOT NULL,
    value               TEXT NOT NULL,
    first_seen_chapter  INTEGER NOT NULL,
    revealed_chapter    INTEGER NOT NULL,
    extraction_method   TEXT NOT NULL CHECK (extraction_method IN ({_METHOD_LIST})),
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
    extraction_method TEXT NOT NULL CHECK (extraction_method IN ({_METHOD_LIST})),
    node_id           INTEGER REFERENCES nodes(id) ON DELETE SET NULL
);

-- Arcs (D6, integration phase): named chapter ranges, structural not extracted.
-- Fencing redacts only the name (F6); the range itself is never spoiler-bearing.
CREATE TABLE IF NOT EXISTS arcs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id       INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    ordinal       INTEGER NOT NULL,
    name          TEXT NOT NULL,
    start_chapter INTEGER NOT NULL,
    end_chapter   INTEGER NOT NULL,
    UNIQUE (work_id, ordinal)
);

-- Entity labels (retrofit R3): the chapter-gated names of an entity. A FENCE
-- SURFACE - a label revealed at chapter k must not appear in any payload at k-1.
-- Carries revealed_chapter like every other reveal-stamped element; no
-- first_seen_chapter, because a label has no existence separate from the chapter the
-- reader is given it (unlike a node, which exists in the text before it is explained).
CREATE TABLE IF NOT EXISTS entity_labels (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id         INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    label             TEXT NOT NULL,
    kind              TEXT NOT NULL CHECK (kind IN ({_LABEL_KIND_LIST})),
    revealed_chapter  INTEGER NOT NULL,
    is_primary        INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    quote             TEXT,
    UNIQUE (entity_id, label, kind)
);

-- Salience (retrofit R6): a DISPLAY rank per (node, chapter), computed only from
-- chapters <= that chapter (rule 7). Not a fence surface: nothing here decides what is
-- SAFE to show, only what is WORTH showing. Cascades with the node.
CREATE TABLE IF NOT EXISTS node_salience (
    node_id   INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    chapter   INTEGER NOT NULL,
    score     REAL NOT NULL,
    rank      INTEGER NOT NULL,
    PRIMARY KEY (node_id, chapter)
);

CREATE INDEX IF NOT EXISTS idx_salience_chapter_rank ON node_salience(chapter, rank);

CREATE INDEX IF NOT EXISTS idx_labels_entity      ON entity_labels(entity_id);
CREATE INDEX IF NOT EXISTS idx_labels_revealed    ON entity_labels(revealed_chapter);
CREATE INDEX IF NOT EXISTS idx_arcs_work         ON arcs(work_id);
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


def _label_from_row(row: sqlite3.Row) -> EntityLabel:
    """SQLite stores is_primary as 0/1; pydantic wants a bool."""
    data = dict(row)
    data["is_primary"] = bool(data["is_primary"])
    return EntityLabel(**data)


class Repository:
    """Thin, fully-typed wrapper over the SQLite connection. The sole SQL surface."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self._db_path = db_path
        path_arg = str(db_path)
        if path_arg != ":memory:":
            Path(path_arg).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: FastAPI runs sync routes in a threadpool, so a repo
        # may be used from a different thread than it was created in. Each request gets
        # its own Repository (see api/deps), so connections are not shared concurrently.
        self.conn = sqlite3.connect(path_arg, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        #: cache for has_entity_labels_table(); None = not yet probed
        self._has_labels: bool | None = None
        #: cache for has_edge_r4_columns(); None = not yet probed
        self._has_edge_r4: bool | None = None
        #: cache for has_node_salience_table(); None = not yet probed
        self._has_salience: bool | None = None

    # --- lifecycle ------------------------------------------------------- #

    def initialize_schema(self) -> None:
        """Create the full 8-type schema if it does not yet exist (idempotent)."""
        # The additive edge migration runs FIRST: on a pre-R4 database the schema
        # script's partial index (`WHERE grade IS NOT NULL`) refers to a column that
        # does not exist yet. On a fresh database the migration is a no-op - there is
        # no `edges` table for it to find - and the DDL below creates both.
        self.migrate_edges_r4()
        self.migrate_edges_relation_vocabulary()
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._has_labels = None  # the schema may have just added entity_labels
        self._has_edge_r4 = None  # ... and the R4 edge columns
        self._has_salience = None  # ... and the R6 salience table

    #: The seven columns retrofit R4 adds to `edges`, with their DDL fragments.
    _EDGE_R4_COLUMNS: tuple[tuple[str, str], ...] = (
        ("weight", "INTEGER NOT NULL DEFAULT 1"),
        ("grade", "TEXT"),
        ("quote", "TEXT"),
        ("quote_chapter", "INTEGER"),
        ("kin_role", "TEXT"),
        ("surface_term", "TEXT"),
        ("subtype", "TEXT"),
    )

    def migrate_edges_r4(self) -> list[str]:
        """Add R4's edge columns to a WRITABLE database created before R4 (idempotent).

        Purely additive: every column is nullable or defaulted, so existing rows keep
        their meaning and every historical Edge still validates. A read-only database
        (the frozen v1 baseline) is never migrated - it is detected by
        :meth:`has_edge_r4_columns` instead and simply reads without these fields.

        The `grade` CHECK constraint is deliberately NOT added by the migration: SQLite
        cannot add a CHECK to an existing table without rewriting it, and rewriting a
        historical table is a bigger risk than the constraint is worth. New databases get
        it from the DDL; :meth:`add_edge` validates the value in Python either way.
        """
        existing = {r["name"] for r in self.conn.execute("PRAGMA table_info(edges)")}
        if not existing:  # no edges table at all -> nothing to migrate
            return []
        added: list[str] = []
        for name, ddl in self._EDGE_R4_COLUMNS:
            if name not in existing:
                self.conn.execute(f"ALTER TABLE edges ADD COLUMN {name} {ddl}")
                added.append(name)
        if added:
            self.conn.commit()
            self._has_edge_r4 = None
        return added

    def migrate_edges_relation_vocabulary(self) -> bool:
        """Widen a pre-R4 `edges.relation` CHECK to admit the twelve new names.

        SQLite cannot alter a CHECK constraint in place, so this is the standard
        create-copy-drop-rename rebuild, run only when the existing constraint is
        actually stale. Returns True if it rebuilt.

        Two safety properties, because rebuilding a table with history in it is the
        riskiest thing in this file:

        * the copy is column-by-column BY NAME, taken from the old table's own
          ``PRAGMA table_info``, so no column is reordered, renamed or dropped; and
        * ``id`` is copied explicitly, so every foreign key and every edge id quoted in
          the evidence files (1325, 1327, ...) still points at the same row.

        A read-only database is never migrated: the caller cannot write to it and the
        probe below simply reports the old vocabulary.
        """
        row = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'edges'"
        ).fetchone()
        if row is None or row["sql"] is None:
            return False  # no edges table yet: the DDL will create it correctly
        if all(f"'{r.value}'" in row["sql"] for r in RELATIONS):
            return False  # already wide enough
        columns = [r["name"] for r in self.conn.execute("PRAGMA table_info(edges)")]
        cols = ", ".join(columns)
        self.conn.execute("PRAGMA foreign_keys = OFF;")
        try:
            self.conn.executescript(_EDGES_DDL.replace("edges", "edges_r4_new", 1))
            self.conn.execute(f"INSERT INTO edges_r4_new ({cols}) SELECT {cols} FROM edges")
            self.conn.execute("DROP TABLE edges")
            self.conn.execute("ALTER TABLE edges_r4_new RENAME TO edges")
            self.conn.commit()
        finally:
            self.conn.execute("PRAGMA foreign_keys = ON;")
        return True

    def has_edge_r4_columns(self) -> bool:
        """Whether this database's `edges` table carries the R4 columns.

        Same role as :meth:`has_entity_labels_table`: the frozen v1 baseline is opened
        read-only and cannot be migrated on the fly, so any query that names `grade` or
        `weight` must ask first and fall back. Probed once and cached.
        """
        if self._has_edge_r4 is None:
            cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(edges)")}
            self._has_edge_r4 = "grade" in cols and "weight" in cols
        return self._has_edge_r4

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

    def list_works(self) -> list[Work]:
        rows = self.conn.execute("SELECT * FROM works ORDER BY id").fetchall()
        return [Work(**dict(r)) for r in rows]

    def get_or_create_work(self, slug: str, title: str) -> int:
        existing = self.get_work_by_slug(slug)
        if existing is not None and existing.id is not None:
            return existing.id
        return self.create_work(Work(slug=slug, title=title))

    def delete_work(self, work_id: int) -> None:
        """TRUE delete: drop the work and every row keyed to it — chapters, chunks,
        nodes, edges, node_properties, mentions — via the schema's ON DELETE CASCADE
        (foreign_keys is ON per connection). The vector index is derived and cleared
        separately by the caller (store.reset)."""
        self.conn.execute("DELETE FROM works WHERE id = ?", (work_id,))
        self.conn.commit()

    # --- arcs (D6, integration phase) ------------------------------------- #

    def set_arcs(self, work_id: int, arcs: list[Arc]) -> None:
        """Replace a work's arcs wholesale (idempotent — arcs are config-derived,
        like everything else knobs-are-data, not incrementally extracted)."""
        self.conn.execute("DELETE FROM arcs WHERE work_id = ?", (work_id,))
        self.conn.executemany(
            """INSERT INTO arcs (work_id, ordinal, name, start_chapter, end_chapter)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (work_id, a.ordinal, a.name, a.start_chapter, a.end_chapter)
                for a in arcs
            ],
        )
        self.conn.commit()

    def list_arcs(self, work_id: int) -> list[Arc]:
        """All arcs, UNFENCED (names included) — for the ingest/seed side, not clients."""
        rows = self.conn.execute(
            "SELECT * FROM arcs WHERE work_id = ? ORDER BY ordinal", (work_id,)
        ).fetchall()
        return [Arc(**dict(r)) for r in rows]

    def list_arcs_fenced(self, work_id: int, chapter: int) -> list[Arc]:
        """Arcs with the name REDACTED (empty string) for any arc not yet started
        (F6, enforced here at the SQL level, not post-filtered by a caller). The
        range itself always shows — it carries no spoiler weight by itself, and the
        chapter picker/Chronicle need the full book's block boundaries to lay out.
        """
        rows = self.conn.execute(
            """SELECT id, work_id, ordinal,
                      CASE WHEN start_chapter <= ? THEN name ELSE '' END AS name,
                      start_chapter, end_chapter
                 FROM arcs
                WHERE work_id = ?
                ORDER BY ordinal""",
            (chapter, work_id),
        ).fetchall()
        return [Arc(**dict(r)) for r in rows]

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

    def add_node(self, node: Node, *, allow_legacy_type: bool = False) -> int:
        """Insert a node. Rejects a non-graph type unless explicitly allowed.

        Enforcement point (b) of retrofit R3: new extraction may only create the four
        GraphNodeType values, so nothing new is ever *stored* as Ability/Concept/Event/
        Title. Historical rows are untouched — this guards writes, not reads.

        ``allow_legacy_type=True`` is the one sanctioned exception, for the seeded
        Hollow Crown demo, whose fixture data predates the retrofit and must stay
        byte-identical (rule I2). It is opt-in on purpose: a new code path that forgets
        about the four types is rejected by default rather than silently admitted.
        """
        if not allow_legacy_type and not is_graph_type(node.type):
            raise ValueError(
                f"node type {node.type.value!r} is not drawable (retrofit R3): new nodes "
                f"must be one of {[t.value for t in GRAPH_NODE_TYPES]}. Its documented "
                f"fate is {LEGACY_TYPE_MAP[node.type].value!r} — see LEGACY_TYPE_MAP in "
                "db/models.py. Pass allow_legacy_type=True only to seed legacy fixtures."
            )
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

    def delete_node(self, node_id: int) -> None:
        """Drop a single node (used by the coref merge to remove a folded-away junk node).

        The schema cascades: any edge still referencing it would be deleted too — so the
        coref merge re-points or deletes the node's edges FIRST, leaving it edgeless, then
        re-points its mentions onto the canonical node, so nothing incident is lost here.
        """
        self.conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        self.conn.commit()

    def get_node(self, node_id: int) -> Node | None:
        row = self.conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return Node(**dict(row)) if row else None

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

    def repoint_mentions(self, work_id: int, from_node_id: int, to_node_id: int) -> int:
        """Move every mention of ``from_node_id`` onto ``to_node_id`` (coref merge).

        Keeps the mention rows (provenance + first-seen evidence) but attributes them to
        the canonical entity, so the folded-away junk node can be deleted without losing
        its evidence. Returns the number of mentions re-pointed.
        """
        cur = self.conn.execute(
            "UPDATE mentions SET node_id = ? WHERE work_id = ? AND node_id = ?",
            (to_node_id, work_id, from_node_id),
        )
        self.conn.commit()
        return cur.rowcount

    # --- edges ----------------------------------------------------------- #

    def add_edge(self, edge: Edge) -> int:
        """Insert one edge. Writes R4's columns when the database has them."""
        if not self.has_edge_r4_columns():
            cur = self.conn.execute(
                """INSERT INTO edges
                     (work_id, source_id, target_id, relation, tier,
                      first_seen_chapter, revealed_chapter, extraction_method,
                      evidence_span)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    edge.work_id, edge.source_id, edge.target_id, edge.relation,
                    edge.tier.value, edge.first_seen_chapter, edge.revealed_chapter,
                    edge.extraction_method.value, edge.evidence_span,
                ),
            )
            self.conn.commit()
            return int(cur.lastrowid or 0)
        cur = self.conn.execute(
            """INSERT INTO edges
                 (work_id, source_id, target_id, relation, tier,
                  first_seen_chapter, revealed_chapter, extraction_method, evidence_span,
                  weight, grade, quote, quote_chapter, kin_role, surface_term, subtype)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.work_id, edge.source_id, edge.target_id, edge.relation,
                edge.tier.value, edge.first_seen_chapter, edge.revealed_chapter,
                edge.extraction_method.value, edge.evidence_span,
                edge.weight,
                edge.grade.value if edge.grade is not None else None,
                edge.quote, edge.quote_chapter, edge.kin_role, edge.surface_term,
                edge.subtype,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def get_edge_by_relation_pair(
        self, work_id: int, relation: str, source_id: int, target_id: int
    ) -> Edge | None:
        """The one edge on this (work, relation, head, tail), if it exists (R4 key)."""
        row = self.conn.execute(
            """SELECT * FROM edges
                WHERE work_id = ? AND relation = ? AND source_id = ? AND target_id = ?""",
            (work_id, relation, source_id, target_id),
        ).fetchone()
        return Edge(**dict(row)) if row is not None else None

    def reinforce_edge(
        self,
        existing: Edge,
        *,
        first_seen_chapter: int,
        revealed_chapter: int,
        grade: RelationGrade | None = None,
        quote: str | None = None,
        quote_chapter: int | None = None,
        surface_term: str | None = None,
    ) -> None:
        """Record repeat evidence for an existing edge: +1 weight, best quote kept.

        This is R4 task 5. The reveal stamps only ever move EARLIER, so reinforcement
        can never push an edge past the fence into a later chapter than it already had.

        Which quote survives is decided here, in Python, rather than in a CASE ladder,
        because the rule has two parts and both matter: a STATED citation always beats an
        INFERRED one (STATED is the only grade the graph serves), and among quotes of the
        same grade the EARLIEST chapter wins (that is the chapter the reader learns it,
        so it is also the edge's revealed_chapter).
        """
        assert existing.id is not None
        keep_quote = existing.quote
        keep_chapter = existing.quote_chapter
        keep_grade = existing.grade
        incoming_better = (
            keep_quote is None
            or (grade is RelationGrade.STATED and keep_grade is not RelationGrade.STATED)
            or (
                grade == keep_grade
                and quote_chapter is not None
                and keep_chapter is not None
                and quote_chapter < keep_chapter
            )
        )
        if incoming_better and quote is not None:
            keep_quote, keep_chapter, keep_grade = quote, quote_chapter, grade
        self.conn.execute(
            """UPDATE edges
                  SET weight = weight + 1,
                      first_seen_chapter = ?,
                      revealed_chapter   = ?,
                      grade = ?, quote = ?, quote_chapter = ?,
                      surface_term = COALESCE(surface_term, ?)
                WHERE id = ?""",
            (
                min(existing.first_seen_chapter, first_seen_chapter),
                min(existing.revealed_chapter, revealed_chapter),
                keep_grade.value if keep_grade is not None else None,
                keep_quote, keep_chapter, surface_term, existing.id,
            ),
        )
        self.conn.commit()

    def add_validator_rejection(
        self,
        work_id: int,
        relation: str,
        reason: str,
        *,
        source_surface: str | None = None,
        target_surface: str | None = None,
        source_id: int | None = None,
        target_id: int | None = None,
        quote: str | None = None,
        quote_chapter: int | None = None,
        detail: str | None = None,
    ) -> int:
        """Log one refused proposal with its reason code (R4 task 3)."""
        cur = self.conn.execute(
            """INSERT INTO validator_rejections
                 (work_id, relation, source_surface, target_surface, source_id,
                  target_id, quote, quote_chapter, reason, detail)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                work_id, relation, source_surface, target_surface, source_id,
                target_id, quote, quote_chapter, reason, detail,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def rejection_counts(self, work_id: int) -> dict[str, int]:
        """Refusals by reason code, for the phase report."""
        rows = self.conn.execute(
            """SELECT reason, COUNT(*) AS n FROM validator_rejections
                WHERE work_id = ? GROUP BY reason ORDER BY n DESC, reason""",
            (work_id,),
        ).fetchall()
        return {str(r["reason"]): int(r["n"]) for r in rows}

    def clear_validator_rejections(self, work_id: int) -> None:
        """Drop this work's rejection log (a rebuild re-derives it)."""
        self.conn.execute("DELETE FROM validator_rejections WHERE work_id = ?", (work_id,))
        self.conn.commit()

    def list_edges(self, work_id: int) -> list[Edge]:
        rows = self.conn.execute(
            "SELECT * FROM edges WHERE work_id = ? ORDER BY id", (work_id,)
        ).fetchall()
        return [Edge(**dict(r)) for r in rows]

    def update_edge_endpoints(self, edge_id: int, source_id: int, target_id: int) -> None:
        """Re-point an edge onto new endpoints (coref merge folds a junk endpoint to POV)."""
        self.conn.execute(
            "UPDATE edges SET source_id = ?, target_id = ? WHERE id = ?",
            (source_id, target_id, edge_id),
        )
        self.conn.commit()

    def update_edge_reveal(
        self, edge_id: int, first_seen_chapter: int, revealed_chapter: int
    ) -> None:
        """Lower an edge's reveal stamps (coref dedup keeps the EARLIEST of the merged pair).

        Used only to take the min when two edges collapse into one; never raises a stamp,
        so the fence can never reveal a merged edge later than it already would have.
        """
        self.conn.execute(
            "UPDATE edges SET first_seen_chapter = ?, revealed_chapter = ? WHERE id = ?",
            (first_seen_chapter, revealed_chapter, edge_id),
        )
        self.conn.commit()

    def delete_edge(self, edge_id: int) -> None:
        """Delete a single edge (coref merge drops self-loops + deduped duplicates)."""
        self.conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
        self.conn.commit()

    def count_edges(self, work_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM edges WHERE work_id = ?", (work_id,)
        ).fetchone()
        return int(row["n"])

    def clear_edges(self, work_id: int) -> None:
        """Drop ALL edges for a work, every tier and every provenance.

        Blunt: it removes relex (Tier-2) and identity (Tier-3) edges too, so a rebuild of
        one producer must NOT use it — use ``clear_edges_by_method`` or
        ``clear_edges_by_tier``, which scope the delete to the edges that producer owns.
        """
        self.conn.execute("DELETE FROM edges WHERE work_id = ?", (work_id,))
        self.conn.commit()

    def clear_edges_by_method(self, work_id: int, method: ExtractionMethod) -> None:
        """Drop only the edges one producer owns, keyed on provenance.

        The Tier-1 co-occurrence builder rebuilds with this so toggling it off (or
        re-running it) can never delete a relex, LLM or hand-curated edge.
        """
        self.conn.execute(
            "DELETE FROM edges WHERE work_id = ? AND extraction_method = ?",
            (work_id, method.value),
        )
        self.conn.commit()

    def clear_edges_by_tier(self, work_id: int, tier: RelationTier) -> None:
        """Drop only one tier's edges (lets Tier-2 rebuild without disturbing Tier-1)."""
        self.conn.execute(
            "DELETE FROM edges WHERE work_id = ? AND tier = ?", (work_id, tier.value)
        )
        self.conn.commit()

    def list_edges_by_tier(self, work_id: int, tier: RelationTier) -> list[Edge]:
        """All edges of a work at one tier (unfenced; for rebuilds + eval, not clients)."""
        rows = self.conn.execute(
            "SELECT * FROM edges WHERE work_id = ? AND tier = ? ORDER BY id",
            (work_id, tier.value),
        ).fetchall()
        return [Edge(**dict(r)) for r in rows]

    # --- entity labels (retrofit R3) -------------------------------------- #

    def add_entity_label(self, label: EntityLabel) -> int:
        """Insert one chapter-gated name for an entity (idempotent on the UNIQUE key)."""
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO entity_labels
                 (entity_id, label, kind, revealed_chapter, is_primary, quote)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                label.entity_id,
                label.label,
                label.kind.value,
                label.revealed_chapter,
                1 if label.is_primary else 0,
                label.quote,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def clear_entity_labels(self, work_id: int) -> None:
        """Drop a work's labels (derived data; extraction rebuilds them)."""
        if not self.has_entity_labels_table():
            return
        self.conn.execute(
            "DELETE FROM entity_labels WHERE entity_id IN "
            "(SELECT id FROM nodes WHERE work_id = ?)",
            (work_id,),
        )
        self.conn.commit()

    def has_entity_labels_table(self) -> bool:
        """Whether this database has the R3 `entity_labels` table.

        A database written before R3 does not, and must still open and SERVE — the frozen
        v1 baseline is exactly such a database and is opened read-only, so it cannot be
        migrated on the fly. The label reads below therefore return empty for it and the
        graph falls back to ``nodes.name``. Probed once and cached: the answer cannot
        change for a live connection except via ``initialize_schema``, which resets it.
        """
        if self._has_labels is None:
            row = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'entity_labels'"
            ).fetchone()
            self._has_labels = row is not None
        return self._has_labels

    def list_entity_labels(self, entity_id: int) -> list[EntityLabel]:
        """Every label of one entity, UNFENCED — for rebuilds and eval, not clients."""
        if not self.has_entity_labels_table():
            return []
        rows = self.conn.execute(
            "SELECT * FROM entity_labels WHERE entity_id = ? ORDER BY id", (entity_id,)
        ).fetchall()
        return [_label_from_row(r) for r in rows]

    # --- the payload query (retrofit R6): FOUR clauses, in order ---------- #

    def graph_payload_nodes(
        self,
        work_id: int,
        chapter: int,
        cast_size: int | None,
        types: Sequence[str],
    ) -> list[Node]:
        """The nodes the graph draws: fence first, then three display clauses.

        Clause order is the point of this method and is fixed by retrofit rule 1:

        1. **FENCE (safety)** -- ``revealed_chapter <= :n``.
        2. **DISPLAY** -- node type in the requested overlays.
        3. **DISPLAY** -- salience rank *among those types* <= cast size (the cast
           dial; v1's was a client-side no-op, defect D3).

        The fence clause is never merged with the display clauses. Reading this SQL you
        can always tell whether a node is missing because it would be a spoiler or
        because the reader turned an overlay off.

        The rank is re-computed over the type-filtered set with a window function
        rather than read from ``node_salience.rank``. R6 [MEASURED] that the stored
        rank is global across all four node types, so "main cast 20" showed only 12
        Characters at chapter 40 -- the number on the dial matched nothing on screen.
        User decision after that measurement; R6's pre-registered miss stands unedited.

        This is *not* a fence change: the window only re-orders rows that the fence has
        already admitted, and each row's score was itself computed from chapters <= n
        (rule 7), so no future information enters the ordering.
        """
        placeholders = ", ".join("?" for _ in types) or "''"
        rank_by_type = cast_size is not None and self.has_node_salience_table()
        params: list[object] = [chapter] if rank_by_type else []
        params += [work_id, chapter]
        params.extend(types)
        # DISPLAY (presentation): the cast dial, applied to the ranked subquery below.
        inner = f"""SELECT n.*,
                           ROW_NUMBER() OVER (ORDER BY s.score DESC, n.id) AS cast_rank
                      FROM nodes n
                      JOIN node_salience s ON s.node_id = n.id AND s.chapter = ?
                      WHERE n.work_id = ?
                        -- FENCE (safety): the reader may not see beyond chapter :n.
                        AND n.revealed_chapter <= ?
                        -- DISPLAY (presentation): the requested node types.
                        AND n.type IN ({placeholders})"""
        if rank_by_type:
            sql = f"SELECT * FROM ({inner}) WHERE cast_rank <= ? ORDER BY id"
            params.append(cast_size)
        else:
            sql = f"""SELECT n.* FROM nodes n
                       WHERE n.work_id = ?
                         -- FENCE (safety): the reader may not see beyond chapter :n.
                         AND n.revealed_chapter <= ?
                         -- DISPLAY (presentation): the requested node types.
                         AND n.type IN ({placeholders})
                       ORDER BY n.id"""
        rows = self.conn.execute(sql, params).fetchall()
        return [Node(**{k: r[k] for k in r.keys() if k in Node.model_fields}) for r in rows]

    def graph_payload_edges(
        self, work_id: int, chapter: int, node_ids: Sequence[int], grades: Sequence[str]
    ) -> list[Edge]:
        """The edges the graph draws: fence first, then the grade display clause.

        1. **FENCE (safety)** -- the edge and BOTH endpoints revealed by ``:n``.
        2. **DISPLAY** -- the endpoints survived the node display clauses above.
        3. **DISPLAY** -- grade in the served set, with ``SAME_AS`` restricted to
           STATED (rule 4 as amended in R7: an identity claim is the most damaging
           thing to get wrong, so the identity family keeps the strict rule).

        A pre-R4 database has no ``grade`` column; there the grade clause is skipped and
        every fenced edge is served, which is what the frozen baseline needs.
        """
        if not node_ids:
            return []
        ids = ", ".join("?" for _ in node_ids)
        params: list[object] = [work_id, chapter, chapter, chapter, *node_ids, *node_ids]
        grade_clause = ""
        if self.has_edge_r4_columns() and grades:
            placeholders = ", ".join("?" for _ in grades)
            # DISPLAY (evidence strength): the served grades, and SAME_AS only when
            # STATED. `grade IS NULL` keeps a pre-R4 database serving: those rows carry
            # no grade at all, and dropping them would blank the frozen baseline.
            grade_clause = (
                f"\n                   AND (e.grade IN ({placeholders}) OR e.grade IS NULL)"
                "\n                   AND (e.relation <> 'SAME_AS' OR e.grade = 'STATED')"
            )
            params.extend(grades)
        rows = self.conn.execute(
            f"""SELECT e.* FROM edges e
                  JOIN nodes hs ON e.source_id = hs.id
                  JOIN nodes ts ON e.target_id = ts.id
                 WHERE e.work_id = ?
                   -- FENCE (safety): edge and BOTH endpoints revealed by :n.
                   AND e.revealed_chapter <= ?
                   AND hs.revealed_chapter <= ?
                   AND ts.revealed_chapter <= ?
                   -- DISPLAY (presentation): both endpoints survived the node clauses.
                   AND e.source_id IN ({ids})
                   AND e.target_id IN ({ids}){grade_clause}
                 ORDER BY e.id""",
            params,
        ).fetchall()
        return [Edge(**dict(r)) for r in rows]

    # --- salience (retrofit R6, DISPLAY data) ----------------------------- #

    def has_node_salience_table(self) -> bool:
        """Whether this database carries R6's `node_salience` table.

        Same role as `has_entity_labels_table`: a pre-R6 database (the frozen baseline)
        must still open and serve, so callers fall back to serving the whole cast.
        """
        if self._has_salience is None:
            row = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='node_salience'"
            ).fetchone()
            self._has_salience = row is not None
        return self._has_salience

    def add_node_salience_bulk(self, rows: list[NodeSalience]) -> int:
        self.conn.executemany(
            """INSERT OR REPLACE INTO node_salience (node_id, chapter, score, rank)
               VALUES (?, ?, ?, ?)""",
            [(r.node_id, r.chapter, r.score, r.rank) for r in rows],
        )
        self.conn.commit()
        return len(rows)

    def clear_node_salience(self, work_id: int) -> None:
        if not self.has_node_salience_table():
            return
        self.conn.execute(
            "DELETE FROM node_salience WHERE node_id IN "
            "(SELECT id FROM nodes WHERE work_id = ?)",
            (work_id,),
        )
        self.conn.commit()

    def list_salience_ranked(
        self, work_id: int, chapter: int, limit: int | None = None
    ) -> list[Node]:
        """The fenced cast at ``chapter``, in rank order, optionally capped.

        The FENCE comes first and the rank is a DISPLAY clause after it (rule 1). The
        rank table is itself per-chapter, so it cannot carry future information.
        """
        if not self.has_node_salience_table():
            return self.list_graph_nodes_revealed(work_id, chapter)
        sql = """SELECT n.* FROM nodes n
                   JOIN node_salience s ON s.node_id = n.id
                  WHERE n.work_id = ?
                    -- FENCE (safety): the reader may not see beyond chapter :n.
                    AND n.revealed_chapter <= ?
                    -- DISPLAY (presentation): this chapter's importance ranking.
                    AND s.chapter = ?
                  ORDER BY s.rank"""
        params: list[object] = [work_id, chapter, chapter]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [Node(**{k: r[k] for k in r.keys() if k in Node.model_fields}) for r in rows]

    def count_nodes_revealed(self, work_id: int, chapter: int) -> int:
        """Fenced node count (retrofit R6 fixes defect D3).

        `count_nodes` counts every row regardless of chapter, so the status endpoint was
        reporting a total that includes entities the reader has not met. That is a
        number leak: it tells a reader at chapter 3 how large the cast eventually gets.
        """
        row = self.conn.execute(
            """SELECT COUNT(*) AS n FROM nodes
                WHERE work_id = ?
                  -- FENCE (safety): never count past the reader's chapter.
                  AND revealed_chapter <= ?""",
            (work_id, chapter),
        ).fetchone()
        return int(row["n"])

    # --- fenced reads (the spoiler fence enforced at the SQL level) ------- #
    # These are the SANCTIONED queries that query/fence.py wraps. Visibility keys on
    # revealed_chapter; edges additionally require BOTH endpoints to be revealed.

    def list_nodes_revealed(self, work_id: int, chapter: int) -> list[Node]:
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE work_id = ? AND revealed_chapter <= ? ORDER BY id",
            (work_id, chapter),
        ).fetchall()
        return [Node(**dict(r)) for r in rows]

    def list_graph_nodes_revealed(self, work_id: int, chapter: int) -> list[Node]:
        """Nodes for the GRAPH payload: fenced first, then filtered to drawable types.

        The two WHERE clauses are deliberately separate and separately commented, per
        retrofit rule 1. The first is the SAFETY fence (``revealed_chapter <= :n``) and
        must come first; the second is a DISPLAY filter (retrofit R3's four drawable
        types) and is applied after it. Merging them would make it impossible to tell,
        reading the SQL, whether a missing node was hidden for spoiler reasons or for
        presentation reasons — and would put a display concern inside the fence.
        """
        rows = self.conn.execute(
            f"""SELECT * FROM nodes
                 WHERE work_id = ?
                   -- FENCE (safety): the reader may not see beyond chapter :n.
                   AND revealed_chapter <= ?
                   -- DISPLAY (presentation, retrofit R3): only drawable types.
                   AND type IN ({_GRAPH_TYPE_LIST})
                 ORDER BY id""",
            (work_id, chapter),
        ).fetchall()
        return [Node(**dict(r)) for r in rows]

    def list_entity_labels_revealed(
        self, work_id: int, chapter: int
    ) -> list[EntityLabel]:
        """Labels the reader may see at chapter N (label AND its entity revealed).

        The same both-endpoints logic as node properties: a name for a character the
        reader has not met is still a spoiler, so the entity's own reveal gates it too.
        """
        if not self.has_entity_labels_table():
            return []  # pre-R3 database: no labels exist to reveal
        rows = self.conn.execute(
            """SELECT l.*
                 FROM entity_labels l
                 JOIN nodes n ON l.entity_id = n.id
                WHERE n.work_id = ?
                  AND l.revealed_chapter <= ?
                  AND n.revealed_chapter <= ?
                ORDER BY l.id""",
            (work_id, chapter, chapter),
        ).fetchall()
        return [_label_from_row(r) for r in rows]

    def display_names_at(self, work_id: int, chapter: int) -> dict[int, str]:
        """entity_id -> the name to show at chapter N, fenced.

        "The most recent label the reader has been given" — ordered by
        ``revealed_chapter`` descending, then a primary label ahead of a secondary one,
        then fuller forms ahead of shorter ones, then the longer string, so the result is
        deterministic rather than dependent on insertion order.

        Only NAMING kinds (full/short/epithet) can become a display name. A title is
        *attached* to a person (R3 task 5), not substituted for their name: once "the
        Warden" is linked to Orin Drask, the graph should still read "Orin Drask" and
        carry the title alongside. Titles and descriptions therefore come back through
        ``list_entity_labels_revealed`` but never win this query.
        """
        if not self.has_entity_labels_table():
            return {}  # pre-R3 database: the graph falls back to nodes.name
        rows = self.conn.execute(
            """SELECT entity_id, label FROM (
                   SELECT l.entity_id AS entity_id,
                          l.label     AS label,
                          ROW_NUMBER() OVER (
                              PARTITION BY l.entity_id
                              ORDER BY l.revealed_chapter DESC,
                                       l.is_primary DESC,
                                       CASE l.kind WHEN 'full' THEN 0
                                                   WHEN 'short' THEN 1
                                                   ELSE 2 END,
                                       LENGTH(l.label) DESC,
                                       l.id
                          ) AS rank
                     FROM entity_labels l
                     JOIN nodes n ON l.entity_id = n.id
                    WHERE n.work_id = ?
                      AND l.revealed_chapter <= ?
                      AND n.revealed_chapter <= ?
                      AND l.kind IN ('full', 'short', 'epithet')
               ) WHERE rank = 1""",
            (work_id, chapter, chapter),
        ).fetchall()
        return {int(r["entity_id"]): str(r["label"]) for r in rows}

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
