# StoryWeave frontend (Phase 8)

A Vite + React + TypeScript view over the fenced FastAPI routes. The **chapter
slider** drives the spoiler fence: every move re-queries the server at chapter `N`,
and the graph shows exactly what `query/fence.py` revealed at `N` — nodes/edges with
`revealed_chapter <= N`, nothing later. **The fence is server-side; the client never
post-filters and never receives unrevealed data.** Newly-revealed elements **bloom**
in (the Wren==Caelum `SECRET_IDENTITY` edge appearing at chapter 2 is the signature
moment).

The app opens on a **library** (`Library.tsx`) — a shelf of works plus **Add a novel**
(`Composer.tsx`): paste a title + text, the server ingests it in-process and runs
extract→relate in the background, and the composer polls `/works/{slug}/status` until
the graph is ready. Inside a work, **Ask the story** (`SearchPanel.tsx`) runs fenced
semantic search *at the current reading position* — the answer and passages can only
quote text revealed by chapter `N`, the same fence as the graph.

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

In-app ingest needs the heavy NLP, so the API shells out to `.venv-ml` for
extract→relate (the serving process stays ML-free). If `.venv-ml` is absent the
chapters are still saved and the composer says so honestly — run `storyweave extract
<slug>` from the CLI and reopen the shelf. Point both servers at the same DB
(`STORYWEAVE_DB_PATH`), since the background job writes via the CLI.
