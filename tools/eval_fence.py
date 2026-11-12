"""Spoiler-fence leak rate: every reveal-stamped element on every story surface.

DELIVERABLE 1 of the v1 evaluation. For every work in the database and every chapter
``n`` from 1 to that work's ``max_chapter``, this requests each API surface that returns
story content exactly as a client would -- through the real FastAPI app, over the real
``query/fence.py`` and ``db/repository.py`` -- and asserts that no returned element
carries ``revealed_chapter > n``.

The surfaces were found by reading the route table in ``storyweave/api/app.py`` rather
than assumed; ``surfaces()`` documents each route and why it is or is not tested, and the
stdout summary prints that table so the TESTED SURFACE is always stated with the number.

Nothing here re-implements SQL or re-implements the fence. The checker reads the wire
payload; the only database access is the read-only lookup that resolves a graph node's
``properties`` dict (which carries no reveal stamp on the wire) back to the
``node_properties`` rows that could have produced it.

Negative controls (so a zero is not vacuous) -- both run against a COPY of the database
in a temporary directory, which is deleted afterwards; the measured database is opened
``mode=ro`` and is never written:

* ``injected`` -- a synthetic node, edge and node-property with ``revealed_chapter = n+1``
  are INSERTed into the copy. The payload is then fetched at chapter ``n+1`` (where the
  fence correctly emits them, proving the injected rows really do reach the serializer)
  and the checker is run with the bound ``n``. It must flag all three.
* ``sabotaged`` -- the app is served from the copy through a Repository subclass whose
  three fenced reads ignore the chapter argument, i.e. a deliberately broken fence. The
  payload is fetched at chapter ``n`` as a client would. The checker must report
  violations on the surfaces that leak.

Usage:
    python tools/eval_fence.py --db storyweave-demo.sqlite --out evidence/fence_leaks.csv
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sqlite3
import stat
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Make the repo root importable when run as `python tools/eval_fence.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from storyweave.api.app import API_PREFIX, create_app  # noqa: E402
from storyweave.api.deps import get_repository  # noqa: E402
from storyweave.db.models import (  # noqa: E402
    Edge,
    EntityLabel,
    LabelKind,
    Node,
    NodeProperty,
    RelationTier,
)
from storyweave.db.repository import Repository  # noqa: E402
from tools import swconfig  # noqa: E402

#: CSV columns for a recorded violation, in order.
FIELDNAMES: tuple[str, ...] = (
    "run",
    "slug",
    "chapter",
    "endpoint",
    "element_kind",
    "element_id",
    "element_revealed_chapter",
    "detail",
)

# --------------------------------------------------------------------------- #
# The surface table: read off storyweave/api/app.py's router, not assumed.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Surface:
    """One API route, and this harness's disposition toward it."""

    path: str
    tested: bool
    element_kinds: tuple[str, ...]
    note: str


SURFACES: tuple[Surface, ...] = (
    Surface(
        "GET /works/{slug}/entities?n=",
        True,
        ("entity",),
        "EntityModel carries revealed_chapter directly.",
    ),
    Surface(
        "GET /works/{slug}/graph?n=",
        True,
        ("graph_node", "graph_edge", "graph_node_property"),
        "Cytoscape elements; node.properties is a bare key->value dict with no reveal "
        "stamp on the wire, so it is resolved back to node_properties rows read-only.",
    ),
    Surface(
        "GET /works/{slug}/entity/{id}?n=",
        True,
        ("detail_entity", "detail_edge", "detail_property"),
        "Requested for EVERY node id of the work at every chapter, so a not-yet-revealed "
        "id must 404 rather than serve; a 200 on an unrevealed id is itself a violation.",
    ),
    Surface(
        "GET /works/{slug}/entity/{id}/ego?n=",
        True,
        ("ego_entity", "ego_neighbour"),
        "Retrofit R6. Requested for EVERY node id at every chapter: an unrevealed id "
        "must 404, and every neighbour returned must itself be revealed by n.",
    ),
    Surface(
        "GET /works/{slug}/status?n=",
        True,
        ("status_count",),
        "Retrofit R6 (defect D3). The count is not an element with a reveal stamp, so "
        "the rule checked is arithmetic: node_count at n must never exceed the number "
        "of nodes whose revealed_chapter <= n. v1 returned the book-wide total, which "
        "told a chapter-3 reader how large the cast eventually gets.",
    ),
    Surface(
        "salience ranking (repository.list_salience_ranked)",
        True,
        ("salience_rank",),
        "Retrofit R6. Not an HTTP surface: the cast dial reads it, so a node unrevealed "
        "at n must not appear in ANY rank list at n, or the ordering itself leaks who "
        "matters later.",
    ),
    Surface(
        "GET /works/{slug}/arcs?n=",
        True,
        ("arc_name",),
        "Arcs carry no revealed_chapter. Their fence rule (F6) is name redaction: an arc "
        "with start_chapter > n must send name=null. That rule is what is checked.",
    ),
    Surface(
        "GET /works/{slug}/search?n=&q=",
        False,
        (),
        "NOT TESTED: the vector store directory (.chroma) does not exist in this "
        "checkout, so there is no index to query and the route cannot be exercised "
        "without first building one. Its fence key is chunk chapter_ordinal <= n.",
    ),
    Surface(
        "GET /works/{slug}/status?n/a",
        False,
        (),
        "NOT TESTED as a leak surface: it returns no story element, only an UNFENCED "
        "node_count (repository.count_nodes ignores the chapter). That is a count, not "
        "an element carrying revealed_chapter, so it is out of this metric's scope -- "
        "recorded here because it is a real side channel the checker does not cover.",
    ),
    Surface(
        "GET /works",
        False,
        (),
        "NOT TESTED: work slug/title/chapter_count only; no reveal-stamped element.",
    ),
    Surface(
        "GET /health",
        False,
        (),
        "NOT TESTED: liveness only; no story content.",
    ),
    Surface(
        "POST /works, POST /works/preview, POST /works/{slug}/chapters, "
        "DELETE /works/{slug}",
        False,
        (),
        "NOT TESTED: write/ingest routes. They return counts and echo the caller's own "
        "submitted text; they serve no reveal-stamped element from the graph.",
    ),
)


def tested_surfaces() -> tuple[Surface, ...]:
    return tuple(s for s in SURFACES if s.tested)


# --------------------------------------------------------------------------- #
# Violations
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Violation:
    slug: str
    chapter: int
    endpoint: str
    element_kind: str
    element_id: str
    element_revealed_chapter: int | str
    detail: str


@dataclass
class Tally:
    """What a run inspected. ``queries`` counts HTTP requests actually issued."""

    queries: int = 0
    elements: int = 0
    by_kind: Counter[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.by_kind is None:
            self.by_kind = Counter()

    def count(self, kind: str, n: int = 1) -> None:
        self.elements += n
        self.by_kind[kind] += n


# --------------------------------------------------------------------------- #
# The checker
# --------------------------------------------------------------------------- #


class PropertyResolver:
    """Resolves a graph node's wire ``properties`` dict back to its DB reveal stamps.

    ``graph/serialize.py`` emits ``properties`` as ``{key: value}`` with no
    ``revealed_chapter``, so the only way to check that entry is to ask the database
    which ``node_properties`` rows could have produced it. A pair is a violation when
    EVERY row matching (node_id, key, value) has ``revealed_chapter > n`` -- i.e. no
    revealed row could have produced it. Read-only; no SQL beyond this lookup.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._reveals: dict[tuple[int, str, str], list[int]] = {}
        for row in conn.execute(
            "SELECT node_id, key, value, revealed_chapter FROM node_properties"
        ):
            self._reveals.setdefault((int(row[0]), str(row[1]), str(row[2])), []).append(
                int(row[3])
            )

    def min_reveal(self, node_id: int, key: str, value: str) -> int | None:
        """Earliest chapter at which this exact pair could legitimately appear."""
        reveals = self._reveals.get((node_id, key, value))
        return min(reveals) if reveals else None


def check_entities(
    payload: dict[str, Any], slug: str, n: int, tally: Tally
) -> list[Violation]:
    out: list[Violation] = []
    for entity in payload["entities"]:
        tally.count("entity")
        if entity["revealed_chapter"] > n:
            out.append(
                Violation(
                    slug, n, "GET /works/{slug}/entities", "entity",
                    str(entity["id"]), entity["revealed_chapter"],
                    f"entity {entity['name']!r} revealed at "
                    f"{entity['revealed_chapter']} served at n={n}",
                )
            )
    return out


def check_graph(
    payload: dict[str, Any],
    slug: str,
    n: int,
    tally: Tally,
    resolver: PropertyResolver,
) -> list[Violation]:
    out: list[Violation] = []
    endpoint = "GET /works/{slug}/graph"
    revealed_at: dict[str, int] = {}
    for node in payload["elements"]["nodes"]:
        data = node["data"]
        tally.count("graph_node")
        revealed_at[str(data["id"])] = data["revealed_chapter"]
        if data["revealed_chapter"] > n:
            out.append(
                Violation(
                    slug, n, endpoint, "graph_node", str(data["id"]),
                    data["revealed_chapter"],
                    f"node {data['label']!r} revealed at {data['revealed_chapter']}",
                )
            )
        # entity_labels (retrofit R3) are a FENCE SURFACE: every label the payload
        # carries must be revealed at or before n, and so must the node holding it.
        for label in data.get("labels") or []:
            tally.count("graph_node_label")
            label_reveal = int(label["revealed_chapter"])
            if label_reveal > n:
                out.append(
                    Violation(
                        slug, n, endpoint, "graph_node_label",
                        f"{data['id']}:{label['label']}", label_reveal,
                        f"label {label['label']!r} ({label['kind']}) on node "
                        f"{data['id']} is revealed at {label_reveal}",
                    )
                )
            if data["revealed_chapter"] > n:
                out.append(
                    Violation(
                        slug, n, endpoint, "graph_node_label",
                        f"{data['id']}:{label['label']}", data["revealed_chapter"],
                        f"label {label['label']!r} rides an unrevealed node "
                        f"{data['id']} (both-rule)",
                    )
                )
        # The displayed name must itself be a revealed label (or the node's own name in a
        # pre-R3 database, which carries no separate label reveal).
        visible_labels = {str(x["label"]) for x in (data.get("labels") or [])}
        if visible_labels and str(data["label"]) not in visible_labels:
            out.append(
                Violation(
                    slug, n, endpoint, "graph_node_label",
                    f"{data['id']}:display", "unmatched",
                    f"display name {data['label']!r} is not among the revealed labels "
                    f"{sorted(visible_labels)} -- reveal stamp unverifiable",
                )
            )
        for key, value in (data.get("properties") or {}).items():
            tally.count("graph_node_property")
            earliest = resolver.min_reveal(int(data["id"]), key, str(value))
            if earliest is None:
                out.append(
                    Violation(
                        slug, n, endpoint, "graph_node_property",
                        f"{data['id']}:{key}", "unmatched",
                        f"property {key}={value!r} on node {data['id']} matches no "
                        f"node_properties row -- reveal stamp unverifiable",
                    )
                )
            elif earliest > n:
                out.append(
                    Violation(
                        slug, n, endpoint, "graph_node_property",
                        f"{data['id']}:{key}", earliest,
                        f"property {key}={value!r} on node {data['id']} is revealed no "
                        f"earlier than {earliest}",
                    )
                )
    for edge in payload["elements"]["edges"]:
        data = edge["data"]
        tally.count("graph_edge")
        if data["revealed_chapter"] > n:
            out.append(
                Violation(
                    slug, n, endpoint, "graph_edge", str(data["id"]),
                    data["revealed_chapter"],
                    f"edge {data['relation']} {data['source']}->{data['target']}",
                )
            )
        # The both-endpoints rule is part of the fence's contract, so it is checked too:
        # an edge may not be served when either endpoint is unrevealed at n.
        for role in ("source", "target"):
            endpoint_reveal = revealed_at.get(str(data[role]))
            if endpoint_reveal is None:
                out.append(
                    Violation(
                        slug, n, endpoint, "graph_edge", str(data["id"]), "dangling",
                        f"edge {role} {data[role]} is not among the served nodes "
                        f"(both-endpoints rule)",
                    )
                )
            elif endpoint_reveal > n:
                out.append(
                    Violation(
                        slug, n, endpoint, "graph_edge", str(data["id"]), endpoint_reveal,
                        f"edge {role} {data[role]} revealed at {endpoint_reveal}",
                    )
                )
    return out


def check_ego(
    payload: dict[str, Any], slug: str, n: int, tally: Tally, revealed_by: dict[int, int]
) -> list[Violation]:
    """Retrofit R6: the ego view must not name an unrevealed entity or tie."""
    out: list[Violation] = []
    endpoint = "GET /works/{slug}/entity/{id}/ego"
    entity = payload["entity"]
    tally.count("ego_entity")
    if entity["revealed_chapter"] > n:
        out.append(Violation(
            slug, n, endpoint, "ego_entity", str(entity["id"]),
            entity["revealed_chapter"], f"ego of {entity['name']!r} served at n={n}",
        ))
    for nb in payload["neighbours"]:
        tally.count("ego_neighbour")
        reveal = revealed_by.get(nb["entity_id"])
        if reveal is not None and reveal > n:
            out.append(Violation(
                slug, n, endpoint, "ego_neighbour", str(nb["entity_id"]), reveal,
                f"neighbour {nb['name']!r} of entity {entity['id']} revealed at {reveal}",
            ))
    return out


def check_status(
    payload: dict[str, Any], slug: str, n: int, tally: Tally, revealed_by: dict[int, int]
) -> list[Violation]:
    """Retrofit R6 / defect D3: the count must not exceed what the fence allows."""
    tally.count("status_count")
    allowed = sum(1 for reveal in revealed_by.values() if reveal <= n)
    served = int(payload["node_count"])
    if served > allowed:
        return [Violation(
            slug, n, "GET /works/{slug}/status", "status_count", "node_count",
            served, f"status reported {served} nodes at n={n}, fence allows {allowed}",
        )]
    return []


def check_salience(
    ranked_ids: list[int], slug: str, n: int, tally: Tally, revealed_by: dict[int, int]
) -> list[Violation]:
    """Retrofit R6: a node unrevealed at n must not appear in the rank list at n."""
    out: list[Violation] = []
    for node_id in ranked_ids:
        tally.count("salience_rank")
        reveal = revealed_by.get(node_id)
        if reveal is not None and reveal > n:
            out.append(Violation(
                slug, n, "salience ranking", "salience_rank", str(node_id), reveal,
                f"node {node_id} ranked at n={n} but revealed at {reveal}",
            ))
    return out


def check_entity_detail(
    payload: dict[str, Any], slug: str, n: int, tally: Tally
) -> list[Violation]:
    out: list[Violation] = []
    endpoint = "GET /works/{slug}/entity/{id}"
    entity = payload["entity"]
    tally.count("detail_entity")
    if entity["revealed_chapter"] > n:
        out.append(
            Violation(
                slug, n, endpoint, "detail_entity", str(entity["id"]),
                entity["revealed_chapter"],
                f"entity {entity['name']!r} served at n={n}",
            )
        )
    for edge in payload["edges"]:
        tally.count("detail_edge")
        if edge["revealed_chapter"] > n:
            out.append(
                Violation(
                    slug, n, endpoint, "detail_edge", str(edge["id"]),
                    edge["revealed_chapter"],
                    f"edge {edge['relation']} on entity {entity['id']}",
                )
            )
    for prop in payload["properties"]:
        tally.count("detail_property")
        if prop["revealed_chapter"] > n:
            out.append(
                Violation(
                    slug, n, endpoint, "detail_property",
                    f"{entity['id']}:{prop['key']}", prop["revealed_chapter"],
                    f"property {prop['key']}={prop['value']!r}",
                )
            )
    return out


def check_arcs(payload: dict[str, Any], slug: str, n: int, tally: Tally) -> list[Violation]:
    """F6: an arc whose start_chapter > n must send name=null."""
    out: list[Violation] = []
    for arc in payload["arcs"]:
        tally.count("arc_name")
        if arc["start_chapter"] > n and arc["name"] is not None:
            out.append(
                Violation(
                    slug, n, "GET /works/{slug}/arcs", "arc_name", str(arc["ordinal"]),
                    arc["start_chapter"],
                    f"arc {arc['ordinal']} name {arc['name']!r} sent although it starts "
                    f"at chapter {arc['start_chapter']}",
                )
            )
    return out


# --------------------------------------------------------------------------- #
# Driving the real app
# --------------------------------------------------------------------------- #


def make_client(repo: Repository) -> TestClient:
    """The real FastAPI app, bound to one already-open Repository."""
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repo
    return TestClient(app)


def sweep_work(
    client: TestClient,
    resolver: PropertyResolver,
    slug: str,
    chapters: list[int],
    node_ids: list[int],
    revealed_at: dict[int, int],
    tally: Tally,
    check_bound: int | None = None,
) -> list[Violation]:
    """Every tested surface, every chapter in ``chapters``, one work.

    ``check_bound`` overrides the chapter the checker asserts against (used only by the
    ``injected`` negative control, which fetches at n+1 and checks against n). When it is
    None -- the measurement path -- the asserted bound is the requested chapter itself.
    """
    violations: list[Violation] = []
    base = f"{API_PREFIX}/works/{slug}"
    for chapter in chapters:
        bound = chapter if check_bound is None else check_bound

        response = client.get(f"{base}/entities", params={"n": chapter})
        tally.queries += 1
        response.raise_for_status()
        violations += check_entities(response.json(), slug, bound, tally)

        response = client.get(f"{base}/graph", params={"n": chapter})
        tally.queries += 1
        response.raise_for_status()
        violations += check_graph(response.json(), slug, bound, tally, resolver)

        response = client.get(f"{base}/arcs", params={"n": chapter})
        tally.queries += 1
        response.raise_for_status()
        violations += check_arcs(response.json(), slug, bound, tally)

        # Retrofit R6: the status count is an arithmetic fence surface (defect D3).
        response = client.get(f"{base}/status", params={"n": chapter})
        tally.queries += 1
        response.raise_for_status()
        violations += check_status(response.json(), slug, bound, tally, revealed_at)

        # Every node id, not only the revealed ones: an unrevealed id must 404.
        for node_id in node_ids:
            response = client.get(f"{base}/entity/{node_id}", params={"n": chapter})
            tally.queries += 1
            if response.status_code == 404:
                continue
            response.raise_for_status()
            violations += check_entity_detail(response.json(), slug, bound, tally)

            # Retrofit R6: the ego view of the same id.
            response = client.get(f"{base}/entity/{node_id}/ego", params={"n": chapter})
            tally.queries += 1
            if response.status_code == 404:
                continue
            response.raise_for_status()
            violations += check_ego(response.json(), slug, bound, tally, revealed_at)
    return violations


# --------------------------------------------------------------------------- #
# Negative controls
# --------------------------------------------------------------------------- #

INJECT_CHAPTER = 5  # the bound `n` the negative controls assert against


def _copy_db(src: Path, dest_dir: Path) -> Path:
    dest = dest_dir / "fence_negative_control.db"
    shutil.copy2(src, dest)
    # copy2 preserves the mode bits, so a copy of a read-only source (the frozen
    # baseline DB is chmod'd read-only on purpose) is itself read-only and the
    # injection below fails with "attempt to write a readonly database". The copy
    # is a throwaway in TEMP; make it writable. The source is never touched.
    dest.chmod(stat.S_IWRITE | stat.S_IREAD)
    return dest


def negative_injected(db: Path, slug: str, tmp: Path) -> tuple[list[Violation], Tally]:
    """Inject node + edge + property revealed at n+1; fetch at n+1; check against n."""
    copy = _copy_db(db, tmp)
    with Repository(copy) as repo:
        # A pre-R3 database has no entity_labels table, and the frozen baseline is one.
        # This is the throwaway copy, so adding the table here costs nothing and lets the
        # label canaries run against a legacy database too - which is exactly the case
        # most likely to have a gap. CREATE TABLE IF NOT EXISTS: nothing else changes.
        repo.initialize_schema()
        work = repo.get_work_by_slug(slug)
        assert work is not None and work.id is not None
        anchor = repo.list_nodes_revealed(work.id, 1)[0]
        assert anchor.id is not None
        leak_id = repo.add_node(
            Node(
                work_id=work.id,
                type=anchor.type,
                name="SYNTHETIC LEAK CANARY",
                first_seen_chapter=INJECT_CHAPTER + 1,
                revealed_chapter=INJECT_CHAPTER + 1,
                extraction_method=anchor.extraction_method,
                evidence_span="synthetic negative control",
            )
        )
        repo.add_edge(
            Edge(
                work_id=work.id,
                source_id=anchor.id,
                target_id=leak_id,
                relation="RelatedTo",
                tier=RelationTier.STRUCTURAL,
                first_seen_chapter=INJECT_CHAPTER + 1,
                revealed_chapter=INJECT_CHAPTER + 1,
                extraction_method=anchor.extraction_method,
                evidence_span="synthetic negative control",
            )
        )
        repo.add_node_property(
            NodeProperty(
                node_id=leak_id,
                key="canary",
                value="synthetic",
                first_seen_chapter=INJECT_CHAPTER + 1,
                revealed_chapter=INJECT_CHAPTER + 1,
                extraction_method=anchor.extraction_method,
                evidence_span="synthetic negative control",
            )
        )
        # entity_labels canaries (retrofit R3). TWO of them, because the label surface
        # has two independent ways to leak and each needs its own control:
        #   1. a late label on an EARLY node - the label's own reveal must gate it;
        #   2. an early label on a LATE node - the node's reveal must gate it (both-rule).
        repo.add_entity_label(
            EntityLabel(
                entity_id=anchor.id,
                label="SYNTHETIC LABEL CANARY",
                kind=LabelKind.EPITHET,
                revealed_chapter=INJECT_CHAPTER + 1,
                is_primary=False,
                quote="synthetic negative control",
            )
        )
        repo.add_entity_label(
            EntityLabel(
                entity_id=leak_id,
                label="SYNTHETIC LABEL ON A HIDDEN NODE",
                kind=LabelKind.SHORT,
                revealed_chapter=1,
                is_primary=False,
                quote="synthetic negative control",
            )
        )

    repo = swconfig.open_readonly(copy)
    try:
        work = repo.get_work_by_slug(slug)
        assert work is not None and work.id is not None
        resolver = PropertyResolver(repo.conn)
        tally = Tally()
        client = make_client(repo)
        violations = sweep_work(
            client,
            resolver,
            slug,
            [INJECT_CHAPTER + 1],
            [leak_id],
            {},
            tally,
            check_bound=INJECT_CHAPTER,
        )
        return violations, tally
    finally:
        repo.close()


class UnfencedRepository(Repository):
    """A deliberately BROKEN fence: the three reveal-filtered reads ignore the chapter.

    Used only by the ``sabotaged`` negative control, against a throwaway copy. It proves
    the checker reports violations when the app really does leak, rather than only when a
    bound is shifted by hand.
    """

    def list_nodes_revealed(self, work_id: int, chapter: int) -> list[Node]:
        return self.list_nodes(work_id)

    def list_edges_revealed(self, work_id: int, chapter: int) -> list[Edge]:
        return self.list_edges(work_id)

    def list_node_properties_revealed(
        self, work_id: int, chapter: int
    ) -> list[NodeProperty]:
        out: list[NodeProperty] = []
        for node in self.list_nodes(work_id):
            out += self.list_node_properties(node.id or 0)
        return out


def negative_sabotaged(db: Path, slug: str, tmp: Path) -> tuple[list[Violation], Tally]:
    """Serve the real app over a broken fence at chapter n; the checker must catch it."""
    copy = _copy_db(db, tmp)
    repo = UnfencedRepository(copy)
    try:
        work = repo.get_work_by_slug(slug)
        assert work is not None and work.id is not None
        resolver = PropertyResolver(repo.conn)
        node_ids = [n.id or 0 for n in repo.list_nodes(work.id)]
        tally = Tally()
        client = make_client(repo)
        violations = sweep_work(
            client, resolver, slug, [INJECT_CHAPTER], node_ids[:40], {}, tally
        )
        return violations, tally
    finally:
        repo.close()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def measure(db: Path) -> tuple[list[Violation], Tally, dict[str, int]]:
    """The measurement run: every work, every chapter 1..max_chapter, read-only."""
    repo = swconfig.open_readonly(db)
    try:
        resolver = PropertyResolver(repo.conn)
        client = make_client(repo)
        tally = Tally()
        violations: list[Violation] = []
        per_work: dict[str, int] = {}
        for work in repo.list_works():
            assert work.id is not None
            chapters = sorted(c.ordinal for c in repo.list_chapters(work.id))
            if not chapters:
                per_work[work.slug] = 0
                continue
            sweep = list(range(1, max(chapters) + 1))
            nodes = repo.list_nodes(work.id)
            node_ids = [n.id or 0 for n in nodes]
            revealed_at = {n.id or 0: n.revealed_chapter for n in nodes}
            per_work[work.slug] = max(chapters)
            violations += sweep_work(
                client, resolver, work.slug, sweep, node_ids, revealed_at, tally
            )
            # Retrofit R6: salience is not an HTTP surface, but the cast dial reads it,
            # so it is swept here directly against the same reveal map.
            for chapter in sweep:
                ranked = [
                    node.id or 0
                    for node in repo.list_salience_ranked(work.id, chapter)
                ]
                violations += check_salience(
                    ranked, work.slug, chapter, tally, revealed_at
                )
        return violations, tally, per_work
    finally:
        repo.close()


def write_csv(rows: list[tuple[str, Violation]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(FIELDNAMES)
        for run, v in rows:
            writer.writerow(
                [
                    run, v.slug, v.chapter, v.endpoint, v.element_kind, v.element_id,
                    v.element_revealed_chapter, v.detail,
                ]
            )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default="storyweave-demo.sqlite", type=Path)
    ap.add_argument("--out", default=Path("evidence/fence_leaks.csv"), type=Path)
    ap.add_argument(
        "--negative-slug", default="the-ninth-house",
        help="work used for the two negative controls (run against a throwaway copy)",
    )
    args = ap.parse_args(argv)

    print("=== TESTED SURFACE ===")
    for surface in SURFACES:
        mark = "TESTED    " if surface.tested else "not tested"
        kinds = ", ".join(surface.element_kinds) or "-"
        print(f"  [{mark}] {surface.path}")
        print(f"               element kinds: {kinds}")
        print(f"               {surface.note}")

    violations, tally, per_work = measure(args.db)

    print("\n=== MEASUREMENT RUN ===")
    print(f"database: {args.db.resolve()} (opened mode=ro)")
    for slug, max_chapter in sorted(per_work.items()):
        print(f"  {slug}: chapters 1..{max_chapter}")
    print(f"total queries issued:    {tally.queries}")
    print(f"total elements inspected: {tally.elements}")
    for kind, count in sorted(tally.by_kind.items()):
        print(f"    {kind}: {count}")
    print(f"TOTAL VIOLATIONS: {len(violations)}")
    for v in violations[:50]:
        print(f"    {v}")

    rows: list[tuple[str, Violation]] = [("measurement", v) for v in violations]

    print("\n=== NEGATIVE CONTROLS (throwaway copy; measured DB never written) ===")
    with tempfile.TemporaryDirectory(prefix="storyweave-fence-neg-") as tmpdir:
        tmp = Path(tmpdir)
        inj, inj_tally = negative_injected(args.db, args.negative_slug, tmp)
        print(
            f"  injected: 3 synthetic elements revealed at chapter {INJECT_CHAPTER + 1}, "
            f"payload fetched at {INJECT_CHAPTER + 1}, checked against n={INJECT_CHAPTER}"
        )
        print(f"    queries={inj_tally.queries} elements={inj_tally.elements} "
              f"violations_detected={len(inj)}")
        for v in inj:
            print(f"      {v.element_kind} {v.element_id}: {v.detail}")
        rows += [("negative_injected", v) for v in inj]

        sab, sab_tally = negative_sabotaged(args.db, args.negative_slug, tmp)
        print(
            f"  sabotaged: fenced reads replaced with unfenced ones, payload fetched at "
            f"n={INJECT_CHAPTER} as a client would"
        )
        print(f"    queries={sab_tally.queries} elements={sab_tally.elements} "
              f"violations_detected={len(sab)}")
        sab_kinds: Counter[str] = Counter(v.element_kind for v in sab)
        for kind, count in sorted(sab_kinds.items()):
            print(f"      {kind}: {count}")
        rows += [("negative_sabotaged", v) for v in sab]

    detector_ok = len(inj) >= 3 and len(sab) > 0
    print(f"\nDETECTOR VERIFIED TO FIRE: {detector_ok}")

    write_csv(rows, args.out)
    print(f"wrote {args.out} ({len(rows)} rows)")

    if not detector_ok:
        print("ERROR: the negative controls did not fire -- the zero above is vacuous.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
