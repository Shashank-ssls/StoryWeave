# StoryWeave frontend (Phase 8 — vertical slice)

A Vite + React + TypeScript view over the fenced FastAPI routes. The **chapter
slider** drives the spoiler fence: every move re-queries the server at chapter `N`,
and the graph shows exactly what `query/fence.py` revealed at `N` — nodes/edges with
`revealed_chapter <= N`, nothing later. **The fence is server-side; the client never
post-filters and never receives unrevealed data.** Newly-revealed elements **bloom**
in (the Wren==Caelum `SECRET_IDENTITY` edge appearing at chapter 2 is the signature
moment).

## Run the slice (CC0 sample only)

```sh
# 1. Build the deterministic CC0 demo graph (no ML, no LLM) into a fresh DB:
storyweave seed-demo --db storyweave-demo.sqlite

# 2. Serve the fenced API from that DB (light venv — no ML on the serving path):
STORYWEAVE_DB_PATH=storyweave-demo.sqlite uvicorn storyweave.api.app:app --port 8000

# 3. In another shell, run the frontend (proxies /api -> :8000):
cd frontend
npm install
npm run dev        # http://localhost:5173
```

## Scripts

- `npm run dev` — dev server with API proxy.
- `npm run build` — `tsc -b && vite build` (the green gate).
- `npm run typecheck` — types only.

Scope of this slice: graph view, 8-type legend, the chapter slider + server-side
fence, and the bloom. Multi-novel library, in-app ingest, and the search UI are
deferred (see PROGRESS.md "Deferred — post-Phase-8 hardening pass").
