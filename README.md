# StoryWeave

> A spoiler-aware knowledge engine for web novels.

StoryWeave ingests web-novel chapters and builds a **living knowledge graph** of the
story — characters, places, organizations, items, abilities, concepts, events, and
titles as nodes; typed relationships as edges — plus a **spoiler-aware semantic
search**. The defining principle: **the graph models what the reader has been told by
chapter N, not objective world-truth.** A chapter slider drives this reading position,
and the graph blooms as the reader advances.

Extraction uses **GLiNER** (zero-shot, genre-agnostic, free, local) as the floor, with
an **optional local LLM** enhancement layer. The system runs **fully local and offline
by default**; the LLM is an enhancement, never a dependency.

> See [`SPEC.md`](SPEC.md) for the authoritative design and [`PROGRESS.md`](PROGRESS.md)
> for live status. [`CLAUDE.md`](CLAUDE.md) holds the standing build rules.

## The five non-negotiable rules

1. The graph models revealed reader-knowledge at chapter N, not world-truth.
2. The schema supports the full 8-type ontology and all identity relationships from day one.
3. GLiNER-only extraction is the FLOOR and yields a complete, useful graph by itself.
4. The LLM is a PURE ENHANCEMENT layer, never a dependency (GPU → CPU → Colab fallback).
5. Local-first and free by default; the optional LLM path is OFF by default.

## The 8-type ontology

`Character` · `Place` · `Organization` · `Item` · `Ability` · `Concept` · `Event` · `Title`

Compact core, rich edges: a small fixed label set keeps GLiNER accurate; richness comes
from subtypes, properties, and three tiers of relationships (structural / social /
identity). See SPEC §5.

## Architecture

```
INGESTION  →  EXTRACTION  →  STORES  →  FENCE QUERY LAYER  →  API  →  FRONTEND
 clean/split   GLiNER (floor)   SQLite (truth)   the one chokepoint   FastAPI   React +
 chunk         + LLM (enhance)  vector store     revealed_chapter<=N            Cytoscape
```

- **SQLite is the source of truth.** Graph + vector index are rebuildable from it.
- **All SQL lives in `storyweave/db/repository.py`** — one audit point.
- **All spoiler filtering passes through `storyweave/query/fence.py`** (Phase 5).

## Two-environment setup

| Env        | Python | Purpose                                              |
| ---------- | ------ | --------------------------------------------------- |
| `.venv`    | 3.14   | Light app — FastAPI, CLI, tests, lint, type-check.  |
| `.venv-ml` | 3.12   | Heavy NLP — GLiNER, torch, embeddings, the LLM layer.|

### Light environment (`.venv`)

```bash
py -V:3.14 -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
```

### ML environment (`.venv-ml`)

Stood up in Phase 2 (the environment gate). See `requirements-ml.txt`.

## Quick start

```bash
storyweave version              # print version
storyweave info                 # show config (confirms LLM is off by default)
uvicorn storyweave.api.app:app  # serve the API; GET /api/v1/health
```

## Development gate

```bash
ruff check .
mypy
pytest
```

## Build plan

Phases 0 → 9, one at a time, each ending green and pushed. Phases 0–5 form a complete,
fully-local product (natural early-exit). See SPEC §7.

## License

MIT.
