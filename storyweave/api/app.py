"""FastAPI app — fenced HTTP surface (Phase 6).

Every data route requires the reading position ``n`` as a mandatory query param and
returns 422 when it is missing or out of range (FastAPI validation on a required
``Query(..., ge=0)``). No route returns data except through ``query/fence.py`` — the
routes are thin: validate -> fence -> serialize -> typed response. The layer imports
no ML; the search route's embedder + vector store arrive via overridable dependencies.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response

from storyweave import __version__
from storyweave.api import jobs
from storyweave.api.deps import get_embedder, get_repository, get_vector_store
from storyweave.api.schemas import (
    AnalysisStatusResponse,
    CitationModel,
    EdgeModel,
    EntitiesResponse,
    EntityDetailResponse,
    EntityModel,
    GraphElements,
    GraphResponse,
    HealthResponse,
    HitModel,
    IngestRequest,
    IngestResponse,
    PropertyModel,
    SearchResponse,
    WorkModel,
    WorksResponse,
)
from storyweave.config import get_settings
from storyweave.db.models import Work
from storyweave.db.repository import Repository
from storyweave.demo.seed import DEMO_SLUG
from storyweave.graph.serialize import graph_json
from storyweave.ingest.pipeline import ingest as run_ingest
from storyweave.ingest.pipeline import slugify
from storyweave.query import fence
from storyweave.search.embedder import EmbedderProtocol
from storyweave.search.retriever import compose_answer
from storyweave.search.retriever import search as run_search
from storyweave.search.store import BaseVectorStore

API_PREFIX = "/api/v1"
router = APIRouter(prefix=API_PREFIX)

# Mandatory reading-position param: required (no default) + non-negative => missing or
# out-of-range yields 422 automatically.
ChapterParam = Annotated[int, Query(description="Reading position N (mandatory).", ge=0)]
RepoDep = Annotated[Repository, Depends(get_repository)]


def _require_work(repo: Repository, slug: str) -> Work:
    work = repo.get_work_by_slug(slug)
    if work is None or work.id is None:
        raise HTTPException(status_code=404, detail=f"no work with slug '{slug}'")
    return work


@router.get("/health", response_model=HealthResponse)
def health(repo: RepoDep) -> HealthResponse:
    """Liveness + DB and vector-store status."""
    try:
        works = len(repo.list_works())
        database = "ok"
    except Exception:  # pragma: no cover - defensive
        works, database = 0, "error"
    vector_dir = get_settings().vector_dir
    vector_store = "ready" if Path(vector_dir).exists() else "empty"
    return HealthResponse(
        status="ok",
        version=__version__,
        database=database,
        works=works,
        vector_store=vector_store,
    )


@router.get("/works", response_model=WorksResponse)
def list_works(repo: RepoDep) -> WorksResponse:
    works = [
        WorkModel(
            id=w.id or 0,
            slug=w.slug,
            title=w.title,
            chapter_count=repo.count_chapters(w.id or 0),
        )
        for w in repo.list_works()
    ]
    return WorksResponse(works=works)


@router.post("/works", response_model=IngestResponse, status_code=201)
def ingest_work(body: IngestRequest, repo: RepoDep) -> IngestResponse:
    """In-app ingest: create the work + chapters in-process (ML-free), then kick off
    extract→relate in the background (subprocess to .venv-ml). The graph populates as
    analysis finishes; poll `/works/{slug}/status`."""
    title = body.title.strip()
    text = body.text.strip()
    if not title or not text:
        raise HTTPException(status_code=422, detail="title and text are required")
    slug = slugify(title)
    if repo.get_work_by_slug(slug) is not None:
        raise HTTPException(status_code=409, detail=f"a work named '{title}' already exists")

    tmp = Path(tempfile.gettempdir()) / f"storyweave-ingest-{slug}.txt"
    tmp.write_text(text, encoding="utf-8")
    try:
        report = run_ingest(tmp, repo, slug=slug, title=title)
    finally:
        tmp.unlink(missing_ok=True)
    if report.chapters_added == 0 and report.chapters_updated == 0:
        raise HTTPException(status_code=422, detail="no chapters detected in the text")

    jobs.start_analysis(slug, str(get_settings().db_path))
    status = jobs.get_status(slug)
    return IngestResponse(
        slug=slug,
        title=title,
        chapter_count=repo.count_chapters(report.work_id),
        chunks_added=report.chunks_added,
        state=status.state if status else "queued",
    )


@router.get("/works/{slug}/status", response_model=AnalysisStatusResponse)
def work_status(slug: str, repo: RepoDep) -> AnalysisStatusResponse:
    """Analysis progress for in-app ingest; node_count > 0 means the graph is viewable."""
    work = repo.get_work_by_slug(slug)
    node_count = repo.count_nodes(work.id) if work and work.id else 0
    status = jobs.get_status(slug)
    # A pre-seeded work (e.g. the demo) has no job; it is ready iff it already has nodes.
    state = status.state if status else ("ready" if node_count > 0 else "unknown")
    return AnalysisStatusResponse(
        slug=slug,
        state=state,
        detail=status.detail if status else "",
        node_count=node_count,
    )


@router.delete("/works/{slug}", status_code=204)
def delete_work(
    slug: str,
    repo: RepoDep,
    store: Annotated[BaseVectorStore, Depends(get_vector_store)],
) -> Response:
    """TRUE delete of a user novel: drop its SQLite rows (cascade) + its vector index.
    The CC0 demo is protected — it's the committed, reproducible fixture the build
    depends on. Only LOCAL data is removed; nothing committed changes."""
    work = _require_work(repo, slug)
    if slug == DEMO_SLUG:
        raise HTTPException(status_code=403, detail="The demo novel can't be deleted.")
    repo.delete_work(work.id or 0)
    try:
        store.reset(work.id or 0)  # vectors are derived; SQLite delete is authoritative
    except Exception:  # pragma: no cover - store may be absent/unbuilt for this work
        pass
    jobs.forget(slug)
    return Response(status_code=204)


@router.get("/works/{slug}/entities", response_model=EntitiesResponse)
def list_entities(slug: str, n: ChapterParam, repo: RepoDep) -> EntitiesResponse:
    work = _require_work(repo, slug)
    nodes = fence.visible_nodes(repo, work.id or 0, n)  # fenced
    entities = [EntityModel.from_node(node) for node in nodes]
    return EntitiesResponse(slug=slug, n=n, count=len(entities), entities=entities)


@router.get("/works/{slug}/graph", response_model=GraphResponse)
def get_graph(slug: str, n: ChapterParam, repo: RepoDep) -> GraphResponse:
    work = _require_work(repo, slug)
    payload = graph_json(repo, work.id or 0, n)  # fenced projection
    return GraphResponse(slug=slug, n=n, elements=GraphElements.model_validate(payload["elements"]))


@router.get("/works/{slug}/entity/{entity_id}", response_model=EntityDetailResponse)
def get_entity(slug: str, entity_id: int, n: ChapterParam, repo: RepoDep) -> EntityDetailResponse:
    work = _require_work(repo, slug)
    work_id = work.id or 0
    # Fetch the entity through the fence so a not-yet-revealed node 404s.
    node = next((x for x in fence.visible_nodes(repo, work_id, n) if x.id == entity_id), None)
    if node is None:
        raise HTTPException(status_code=404, detail="entity not found or not yet revealed")
    edges = [
        EdgeModel.from_edge(e)
        for e in fence.visible_edges(repo, work_id, n)
        if entity_id in (e.source_id, e.target_id)
    ]
    properties = [
        PropertyModel.from_property(p)
        for p in fence.visible_node_properties(repo, work_id, n)
        if p.node_id == entity_id
    ]
    return EntityDetailResponse(
        slug=slug, n=n, entity=EntityModel.from_node(node), edges=edges, properties=properties
    )


@router.get("/works/{slug}/search", response_model=SearchResponse)
def search_work(
    slug: str,
    n: ChapterParam,
    repo: RepoDep,
    embedder: Annotated[EmbedderProtocol, Depends(get_embedder)],
    store: Annotated[BaseVectorStore, Depends(get_vector_store)],
    q: Annotated[str, Query(min_length=1, description="Query (mandatory).")],
    top_k: Annotated[int, Query(ge=1, le=50)] = 5,
) -> SearchResponse:
    work = _require_work(repo, slug)
    hits = run_search(q, work.id or 0, n, store, embedder, top_k)  # fenced at the index
    answer = compose_answer(q, hits)
    return SearchResponse(
        slug=slug,
        n=n,
        query=q,
        answer=answer.text,
        citations=[
            CitationModel(
                chunk_id=c.chunk_id,
                chapter_ordinal=c.chapter_ordinal,
                char_start=c.char_start,
                char_end=c.char_end,
            )
            for c in answer.citations
        ],
        hits=[HitModel.from_hit(h) for h in hits],
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="StoryWeave",
        version=__version__,
        description="A spoiler-aware knowledge engine for web novels.",
    )
    app.include_router(router)
    return app


app = create_app()
