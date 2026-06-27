# StoryWeave

> A spoiler-aware knowledge engine for web novels — a living, chapter-fenced knowledge graph that only ever shows you what you’ve already read.

StoryWeave ingests the chapters of a web novel and builds a **knowledge graph** of the
story — characters, places, organizations, items, abilities, concepts, events, and titles
as nodes; typed relationships as edges — together with a **spoiler-aware semantic search**.
Its defining principle: **the graph models what the reader has been told by chapter N, not
the objective truth of the world.** A chapter slider drives this reading position, and the
graph *blooms* as you advance — a secret identity, a hidden allegiance, or a late twist
appears on the exact chapter the text reveals it, and never before.

---

## ⚠️ Disclaimer

- **Personal / portfolio project.** StoryWeave is built as a learning and demonstration
  project. It is provided **as-is**, with no warranty (see [LICENSE](LICENSE)).
- **No copyrighted text is distributed.** The repository ships **only one original,
  CC0-licensed sample novel** (*The Hollow Crown*, under `data/samples/the-hollow-crown/`).
  Any real web-novel text you analyze is **your own responsibility**: it is read from a
  **local, git-ignored** folder (`data/raw/`) and is never committed, uploaded, or
  transmitted. Respect the copyright and terms of service of any source you use.
- **Output is automated and imperfect.** Entities and relationships are produced by
  zero-shot NER (GLiNER) and an optional local LLM. The graph is a *best-effort
  reconstruction* of reader-knowledge, not a curated wiki — expect missing edges and
  occasional mislabels (see [Scope & limitations](#scope--limitations)).
- **Local-first and private by default.** Nothing leaves your machine. The optional LLM
  layer is **off by default**; with it off there are **zero outbound network calls** at
  runtime.
- **Not affiliated** with any author, translator, or publisher.

---

## What it does

- **Spoiler fence (the core idea).** Every node, edge, and significant property carries a
  `revealed_chapter`. A single query chokepoint hides anything the reader hasn’t reached at
  chapter N — applied at the database/index level, never as a fragile post-filter.
- **8-type ontology, rich edges.** `Character · Place · Organization · Item · Ability ·
  Concept · Event · Title`, with subtypes and **three tiers of relationships**: structural
  (rule-based floor), social (optional LLM), and identity (`SAME_AS`, `ALIAS`,
  `SECRET_IDENTITY`, `REINCARNATION`, `TRANSMIGRATED_INTO`).
- **GLiNER floor, LLM enhancement.** A complete, useful graph is produced with **zero LLM**.
  The optional local LLM only *adds* social and identity edges, and degrades gracefully to
  the floor when unavailable.
- **Fenced semantic search.** Retrieval-augmented, chapter-scoped answers that can only quote
  text revealed up to your current position.
- **Interactive graph UI.** React + Cytoscape: a chapter slider that blooms newly-revealed
  entities, a degree filter, salience demotion of background noise, type isolation,
  path-finding (“how is A related to B”), and a detail panel with evidence and provenance.
- **Provenance everywhere.** Every element records its extraction method (`gliner` / `rule`
  / `llm`) and an evidence span, so any fact traces back to its source text.

---

## Installation

StoryWeave uses a **two-environment split** (a deliberate design decision — Python 3.14
lacks wheels for the heavy ML stack):

| Environment | Python | Purpose |
| ----------- | ------ | ------- |
| `.venv`     | 3.14   | Light app — FastAPI, CLI, tests, lint, type-check. No ML deps. |
| `.venv-ml`  | 3.12   | Heavy NLP — GLiNER, PyTorch, embeddings, the optional LLM layer. |

ML imports are lazy, so the package imports cleanly in the light environment; ML-only tests
are skipped there.

### Prerequisites

- **Python 3.14** (light app) and **Python 3.12** (ML pipeline)
- **Node.js 18+** (frontend)
- ~3 GB free disk for model weights; CPU is sufficient (a 4 GB GPU is optional)

### 1. Clone

```bash
git clone <your-fork-url> storyweave
cd storyweave
```

### 2. Light environment (`.venv`) — app, CLI, tests

```bash
# Windows (PowerShell)
py -V:3.14 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# macOS / Linux
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verify:

```bash
storyweave version          # prints the version
storyweave info             # shows config (confirms the LLM layer is OFF by default)
pytest                      # full light-venv test suite (120+ tests)
```

### 3. ML environment (`.venv-ml`) — extraction pipeline

```bash
# Windows
py -V:3.12 -m venv .venv-ml
.venv-ml\Scripts\python -m pip install -U pip
.venv-ml\Scripts\python -m pip install -e .
.venv-ml\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv-ml\Scripts\python -m pip install -r requirements-ml.txt
```

Model weights download to a git-ignored `.hf-cache/` inside the project on first run.
(See `requirements-ml.txt` for pinned versions and cache notes.)

### 4. Frontend

```bash
cd frontend
npm install
```

---

## Quick start (the CC0 demo)

Run the bundled, fully-reproducible demo — no real novel text required:

```bash
# 1. Seed the deterministic demo graph (no ML, no LLM):
storyweave seed-demo --db storyweave-demo.sqlite

# 2. Serve the fenced API (light venv — no ML on the serving path):
#    PowerShell:  $env:STORYWEAVE_DB_PATH="storyweave-demo.sqlite"
STORYWEAVE_DB_PATH=storyweave-demo.sqlite uvicorn storyweave.api.app:app --port 8000

# 3. In another terminal, run the UI (proxies /api -> :8000):
cd frontend && npm run dev          # open http://localhost:5173
```

Drag the chapter slider: the `SECRET_IDENTITY` edge blooms at chapter 2, `ALIAS` at 3, and
the layered `TRANSMIGRATED_INTO` reveal at 4 — the spoiler fence, made visible.

---

## Analyze your own novel (local only)

Place your chapters under `data/raw/<your-novel>/` (git-ignored), then run the pipeline in
the **ML environment**:

```bash
# from the .venv-ml interpreter
storyweave ingest data/raw/my-novel --slug my-novel --db my.sqlite   # clean, split, chunk
storyweave extract my-novel --db my.sqlite                           # GLiNER entities (the floor)
storyweave relate  my-novel --db my.sqlite                           # Tier-1 structural edges
storyweave coref   my-novel --db my.sqlite                           # optional pronoun→POV merge
storyweave index   my-novel --db my.sqlite                           # embeddings for search
```

Optional LLM layers (off by default — require a local runner and `STORYWEAVE_LLM_ENABLED=true`):

```bash
storyweave social   my-novel --db my.sqlite     # Tier-2 social relations
storyweave identity my-novel --db my.sqlite     # Tier-3 identity inference
```

Then serve that database (`STORYWEAVE_DB_PATH=my.sqlite uvicorn ...`) and open the UI.
Per-novel knobs (chapter detection, cleaning, POV for coref, thresholds) live in an optional
`storyweave.toml` beside the text — configuration is **data, never code**.

---

## Architecture

```
INGESTION   →   EXTRACTION    →   STORES         →   FENCE QUERY LAYER   →   API      →   FRONTEND
clean/split     GLiNER (floor)    SQLite (truth)     the one chokepoint      FastAPI      React +
chunk           + LLM (enhance)   vector store       revealed_chapter <= N                Cytoscape
```

- **SQLite is the source of truth.** The graph projection and vector index are derived and
  fully rebuildable from it.
- **All SQL lives in `storyweave/db/repository.py`** — a single audit point.
- **All spoiler filtering passes through `storyweave/query/fence.py`** — the one enforcement
  chokepoint, keyed on `revealed_chapter`.

Package layout: `storyweave/{config, db, ingest, nlp, graph, search, query, api, cli}`, plus
`frontend/`, `eval/`, `tests/`, and `data/{raw, samples, labels}/`.

---

## Scope & limitations

**In scope:** a local, free, offline-by-default pipeline that turns ingested chapters into a
spoiler-fenced knowledge graph and a chapter-scoped semantic search, with an interactive
graph UI. The design favors **precision over recall** — for a spoiler graph, a *missing*
edge is safer than a *false* one.

**Deliberately out of scope / known limits (measured, not hidden):**

- **It is not a novel reader** and does not redistribute any copyrighted text.
- **Extraction quality is bounded by the models.** On the CC0 sample, Tier-2 social-relation
  recall sits around 0.29 (precision 1.00) — many implicit relations need reasoning a small
  local model can’t reliably provide. Lifting it was measured and found to regress precision,
  so it was not shipped.
- **Identity subtype labels can be imprecise** with a small (7B) local model (e.g.
  transmigration vs. reincarnation), even when the reveal timing and the edge itself are
  correct.
- **Coreference is conservative.** First/second/third-person self-reference is merged into a
  configured point-of-view character; ambiguous epithets (“the younger soldier”) are
  deliberately **left unmerged** rather than risk corrupting the graph.
- **The LLM layer is optional and unverified across genres.** It is off by default; several
  enhancements remain gated behind a larger model than the local CPU/4 GB-GPU target.

The authoritative design lives in [`SPEC.md`](SPEC.md); detailed, dated status and the
measurement log live in [`PROGRESS.md`](PROGRESS.md).

---

## Development

```bash
ruff check .        # lint
mypy                # strict type-check
pytest              # tests (light venv)
cd frontend && npm run build   # frontend type-check + production build
```

---

## License

[MIT](LICENSE) © Shashank Singhal. The bundled sample novel *The Hollow Crown* is released
under **CC0** (see `data/samples/the-hollow-crown/LICENSE.md`).
