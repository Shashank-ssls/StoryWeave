"""Phase 6: fenced API routes.

All routes run in the light venv: the search route's embedder + vector store are
injected via dependency overrides (fake embedder + in-memory store), so no ML is
imported. P0 requirement: every data route returns 422 when ``n`` is absent.
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from storyweave.api import jobs
from storyweave.api.app import create_app
from storyweave.api.deps import get_embedder, get_repository, get_vector_store
from storyweave.config import get_settings
from storyweave.db.models import (
    Chapter,
    Chunk,
    Edge,
    ExtractionMethod,
    Node,
    NodeProperty,
    NodeType,
    RelationTier,
    Work,
)
from storyweave.db.repository import Repository
from storyweave.search.retriever import index_work
from storyweave.search.store import InMemoryVectorStore

_DIM = 64


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._v(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self._v(text)

    @staticmethod
    def _v(text: str) -> list[float]:
        v = [0.0] * _DIM
        for w in text.lower().split():
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % _DIM] += 1.0
        return v


def _add_chapter_chunk(repo: Repository, wid: int, ordinal: int, text: str) -> None:
    cid = repo.add_chapter(
        Chapter(work_id=wid, ordinal=ordinal, clean_text=text, content_hash=f"h{ordinal}")
    )
    repo.add_chunk(
        Chunk(chapter_id=cid, work_id=wid, ordinal=0, char_start=0, char_end=len(text),
              text=text, content_hash=f"c{ordinal}")
    )


@pytest.fixture(autouse=True)
def _reset_jobs() -> None:
    """The analysis registry is a module global; isolate it per test."""
    jobs._jobs.clear()


@pytest.fixture
def client() -> tuple[TestClient, dict[str, int]]:
    repo = Repository(":memory:")
    repo.initialize_schema()
    wid = repo.create_work(Work(slug="demo", title="Demo"))
    wren = repo.add_node(Node(work_id=wid, type=NodeType.CHARACTER, name="Wren",
                              first_seen_chapter=1, revealed_chapter=1,
                              extraction_method=ExtractionMethod.GLINER))
    caelum = repo.add_node(Node(work_id=wid, type=NodeType.CHARACTER, name="Prince Caelum",
                                first_seen_chapter=2, revealed_chapter=2,
                                extraction_method=ExtractionMethod.GLINER))
    repo.add_edge(Edge(work_id=wid, source_id=wren, target_id=caelum,
                       relation="SECRET_IDENTITY", tier=RelationTier.IDENTITY,
                       first_seen_chapter=2, revealed_chapter=2,
                       extraction_method=ExtractionMethod.LLM))
    repo.add_node_property(NodeProperty(node_id=wren, key="rank", value="Seer",
                                        first_seen_chapter=5, revealed_chapter=5,
                                        extraction_method=ExtractionMethod.LLM))
    _add_chapter_chunk(repo, wid, 1, "Wren stole a ring in the market.")
    _add_chapter_chunk(repo, wid, 2, "Wren was Prince Caelum the heir.")
    _add_chapter_chunk(repo, wid, 5, "The secretword reveals the Seer rank.")

    store = InMemoryVectorStore()
    index_work(wid, repo, store, FakeEmbedder())

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_embedder] = FakeEmbedder
    app.dependency_overrides[get_vector_store] = lambda: store
    return TestClient(app), {"wid": wid, "wren": wren, "caelum": caelum}


# --- P0: every data route requires n -------------------------------------- #


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/works/demo/entities",
        "/api/v1/works/demo/graph",
        "/api/v1/works/demo/entity/1",
        "/api/v1/works/demo/search?q=hi",
    ],
)
def test_missing_n_returns_422(client: tuple[TestClient, dict[str, int]], path: str) -> None:
    c, _ = client
    assert c.get(path).status_code == 422


def test_negative_n_returns_422(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    assert c.get("/api/v1/works/demo/entities?n=-1").status_code == 422


def test_search_missing_query_returns_422(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    assert c.get("/api/v1/works/demo/search?n=1").status_code == 422


# --- health + works -------------------------------------------------------- #


def test_health(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    body = c.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["works"] == 1


def test_list_works(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    body = c.get("/api/v1/works").json()
    assert len(body["works"]) == 1
    assert body["works"][0]["slug"] == "demo"
    assert body["works"][0]["chapter_count"] == 3


def test_unknown_work_404(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    assert c.get("/api/v1/works/nope/entities?n=1").status_code == 404


# --- in-app ingest + analysis status (Part B) ----------------------------- #


_CH_TEXT = (
    "Chapter 1\nWren stole a ring in the moonlit market.\n\n"
    "Chapter 2\nWren was Prince Caelum, the drowned heir, all along.\n"
)


def test_ingest_creates_work_and_chapters(
    client: tuple[TestClient, dict[str, int]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Don't shell out to .venv-ml in the unit test — record the launch instead.
    launched: list[tuple[str, str]] = []
    monkeypatch.setattr(jobs, "start_analysis", lambda slug, db: launched.append((slug, db)))
    c, _ = client
    resp = c.post("/api/v1/works", json={"title": "The Lantern Keep", "text": _CH_TEXT})
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "the-lantern-keep"
    assert body["chapter_count"] == 2
    assert body["state"] == "queued"
    assert launched == [("the-lantern-keep", str(get_settings().db_path))]
    # The new work is listed and analysis status is reachable.
    assert "the-lantern-keep" in {w["slug"] for w in c.get("/api/v1/works").json()["works"]}


def test_ingest_duplicate_title_409(
    client: tuple[TestClient, dict[str, int]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(jobs, "start_analysis", lambda slug, db: None)
    c, _ = client
    c.post("/api/v1/works", json={"title": "The Lantern Keep", "text": _CH_TEXT})
    dup = c.post("/api/v1/works", json={"title": "The Lantern Keep", "text": _CH_TEXT})
    assert dup.status_code == 409


def test_ingest_empty_text_422(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    assert c.post("/api/v1/works", json={"title": "x", "text": "   "}).status_code == 422


def test_status_reflects_job_state(
    client: tuple[TestClient, dict[str, int]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(jobs, "start_analysis", lambda slug, db: jobs._set(slug, "extracting"))
    c, _ = client
    c.post("/api/v1/works", json={"title": "The Lantern Keep", "text": _CH_TEXT})
    st = c.get("/api/v1/works/the-lantern-keep/status").json()
    assert st["state"] == "extracting"
    assert st["node_count"] == 0
    # A pre-seeded work with nodes but no job reads as ready.
    seeded = c.get("/api/v1/works/demo/status").json()
    assert seeded["state"] == "ready"
    assert seeded["node_count"] >= 1


# --- delete a work (true delete; demo protected) -------------------------- #


def test_delete_user_work_removes_all_its_data(
    client: tuple[TestClient, dict[str, int]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(jobs, "start_analysis", lambda slug, db: None)
    c, ids = client
    # Ingest a user novel, then delete it.
    c.post("/api/v1/works", json={"title": "The Lantern Keep", "text": _CH_TEXT})
    assert c.get("/api/v1/works/the-lantern-keep/status").status_code == 200
    resp = c.delete("/api/v1/works/the-lantern-keep")
    assert resp.status_code == 204
    # Gone from the listing and 404 on read; the demo work is untouched.
    slugs = {w["slug"] for w in c.get("/api/v1/works").json()["works"]}
    assert "the-lantern-keep" not in slugs
    assert "demo" in slugs
    assert c.get("/api/v1/works/the-lantern-keep/entities?n=1").status_code == 404


def test_delete_cascades_rows(client: tuple[TestClient, dict[str, int]]) -> None:
    # The seeded 'demo' work has nodes/chapters; deleting it must cascade. We use the
    # repo directly to prove the cascade, independent of the route's demo guard.
    c, ids = client
    repo = c.app.dependency_overrides[get_repository]()  # type: ignore[attr-defined]
    wid = ids["wid"]
    assert repo.count_nodes(wid) > 0
    repo.delete_work(wid)
    assert repo.get_work(wid) is None
    assert repo.count_nodes(wid) == 0
    assert repo.count_chapters(wid) == 0


def test_delete_demo_is_forbidden(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    # Seed a work under the protected demo slug; the route must refuse to delete it.
    from storyweave.demo.seed import DEMO_SLUG  # noqa: PLC0415

    repo = c.app.dependency_overrides[get_repository]()  # type: ignore[attr-defined]
    repo.create_work(Work(slug=DEMO_SLUG, title="The Hollow Crown"))
    resp = c.delete(f"/api/v1/works/{DEMO_SLUG}")
    assert resp.status_code == 403
    assert repo.get_work_by_slug(DEMO_SLUG) is not None


def test_delete_unknown_work_404(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    assert c.delete("/api/v1/works/ghost").status_code == 404


# --- fenced reads ---------------------------------------------------------- #


def test_entities_are_fenced(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    at1 = c.get("/api/v1/works/demo/entities?n=1").json()
    assert {e["name"] for e in at1["entities"]} == {"Wren"}
    at2 = c.get("/api/v1/works/demo/entities?n=2").json()
    assert {e["name"] for e in at2["entities"]} == {"Wren", "Prince Caelum"}


def test_graph_is_fenced(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    at1 = c.get("/api/v1/works/demo/graph?n=1").json()
    assert len(at1["elements"]["nodes"]) == 1
    assert at1["elements"]["edges"] == []
    at2 = c.get("/api/v1/works/demo/graph?n=2").json()
    assert len(at2["elements"]["nodes"]) == 2
    assert at2["elements"]["edges"][0]["data"]["relation"] == "SECRET_IDENTITY"


def test_entity_detail_with_edges_and_properties(
    client: tuple[TestClient, dict[str, int]],
) -> None:
    c, ids = client
    wren = ids["wren"]
    # At n=2: identity edge visible, secret rank property still hidden (revealed ch5).
    at2 = c.get(f"/api/v1/works/demo/entity/{wren}?n=2").json()
    assert at2["entity"]["name"] == "Wren"
    assert any(e["relation"] == "SECRET_IDENTITY" for e in at2["edges"])
    assert at2["properties"] == []
    # At n=5: the property is now revealed.
    at5 = c.get(f"/api/v1/works/demo/entity/{wren}?n=5").json()
    assert any(p["key"] == "rank" and p["value"] == "Seer" for p in at5["properties"])


def test_entity_detail_404_for_unrevealed(client: tuple[TestClient, dict[str, int]]) -> None:
    c, ids = client
    # Prince Caelum is not revealed until ch2 -> 404 at n=1.
    assert c.get(f"/api/v1/works/demo/entity/{ids['caelum']}?n=1").status_code == 404


def test_search_is_fenced(client: tuple[TestClient, dict[str, int]]) -> None:
    c, _ = client
    at2 = c.get("/api/v1/works/demo/search?n=2&q=secretword").json()
    assert all(h["chapter_ordinal"] != 5 for h in at2["hits"])  # ch5 fenced out
    at5 = c.get("/api/v1/works/demo/search?n=5&q=secretword").json()
    assert any(h["chapter_ordinal"] == 5 for h in at5["hits"])
    assert "answer" in at5 and isinstance(at5["citations"], list)
