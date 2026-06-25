"""Pydantic response models for the API (Phase 6).

Every route returns a typed model, never a raw dict. Conversion helpers map the
persistence models / fenced projections onto these wire shapes.
"""

from __future__ import annotations

from pydantic import BaseModel

from storyweave.db.models import Edge, Node, NodeProperty
from storyweave.search.store import SearchHit


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    works: int
    vector_store: str


class WorkModel(BaseModel):
    id: int
    slug: str
    title: str
    chapter_count: int


class WorksResponse(BaseModel):
    works: list[WorkModel]


class IngestRequest(BaseModel):
    title: str
    text: str


class IngestResponse(BaseModel):
    slug: str
    title: str
    chapter_count: int
    chunks_added: int
    state: str  # analysis state (queued/extracting/…)


class AnalysisStatusResponse(BaseModel):
    slug: str
    state: str  # queued | extracting | relating | ready | error
    detail: str
    node_count: int  # > 0 once entities exist (the graph is ready to view)


class EntityModel(BaseModel):
    id: int
    name: str
    type: str
    subtype: str | None = None
    importance: float
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: str
    evidence_span: str | None = None

    @classmethod
    def from_node(cls, n: Node) -> EntityModel:
        return cls(
            id=n.id or 0,
            name=n.name,
            type=n.type.value,
            subtype=n.subtype,
            importance=n.importance,
            first_seen_chapter=n.first_seen_chapter,
            revealed_chapter=n.revealed_chapter,
            extraction_method=n.extraction_method.value,
            evidence_span=n.evidence_span,
        )


class EntitiesResponse(BaseModel):
    slug: str
    n: int
    count: int
    entities: list[EntityModel]


class EdgeModel(BaseModel):
    id: int
    source_id: int
    target_id: int
    relation: str
    tier: int
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: str
    evidence_span: str | None = None

    @classmethod
    def from_edge(cls, e: Edge) -> EdgeModel:
        return cls(
            id=e.id or 0,
            source_id=e.source_id,
            target_id=e.target_id,
            relation=e.relation,
            tier=int(e.tier),
            first_seen_chapter=e.first_seen_chapter,
            revealed_chapter=e.revealed_chapter,
            extraction_method=e.extraction_method.value,
            evidence_span=e.evidence_span,
        )


class PropertyModel(BaseModel):
    key: str
    value: str
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: str
    evidence_span: str | None = None

    @classmethod
    def from_property(cls, p: NodeProperty) -> PropertyModel:
        return cls(
            key=p.key,
            value=p.value,
            first_seen_chapter=p.first_seen_chapter,
            revealed_chapter=p.revealed_chapter,
            extraction_method=p.extraction_method.value,
            evidence_span=p.evidence_span,
        )


class EntityDetailResponse(BaseModel):
    slug: str
    n: int
    entity: EntityModel
    edges: list[EdgeModel]
    properties: list[PropertyModel]


# --- graph (Cytoscape, but fully typed) ------------------------------------ #


class GraphNodeData(BaseModel):
    id: str
    label: str
    type: str
    subtype: str | None = None
    importance: float
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: str
    evidence_span: str | None = None
    properties: dict[str, str] = {}


class GraphEdgeData(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    tier: int
    first_seen_chapter: int
    revealed_chapter: int
    extraction_method: str
    evidence_span: str | None = None


class GraphNode(BaseModel):
    data: GraphNodeData


class GraphEdge(BaseModel):
    data: GraphEdgeData


class GraphElements(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphResponse(BaseModel):
    slug: str
    n: int
    elements: GraphElements


# --- search ---------------------------------------------------------------- #


class CitationModel(BaseModel):
    chunk_id: int
    chapter_ordinal: int
    char_start: int
    char_end: int


class HitModel(BaseModel):
    chunk_id: int
    chapter_ordinal: int
    char_start: int
    char_end: int
    text: str
    score: float

    @classmethod
    def from_hit(cls, h: SearchHit) -> HitModel:
        return cls(
            chunk_id=h.chunk_id,
            chapter_ordinal=h.chapter_ordinal,
            char_start=h.char_start,
            char_end=h.char_end,
            text=h.text,
            score=h.score,
        )


class SearchResponse(BaseModel):
    slug: str
    n: int
    query: str
    answer: str
    citations: list[CitationModel]
    hits: list[HitModel]
