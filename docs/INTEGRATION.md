# StoryWeave — Integration phase

> Branch `integration/demo-scale`, off `main` (which now has the merged R0–R9 redesign).
> Full frontend ↔ backend assimilation + a second, demo-scale (~40 chapter) novel.
> Every claim below is labeled MEASURED (ran it, saw it) / ASSERTED (reasoned, not run) /
> BROKEN. Runner summary lines are quoted verbatim, not paraphrased. See `CLAUDE.md`'s
> "Integration phase" section for the phase's rules (I1–I6).

---

## Part A — Recon (read-only)

### A1. How the Hollow Crown demo is produced and seeded

**Two separate things share the name "Hollow Crown," and they are NOT the same
pipeline** — this is the single most important recon finding for Part B:

1. **Source text**: `data/samples/the-hollow-crown/ch01.txt`…`ch04.txt` (committed, CC0,
   `LICENSE.md` beside them) + `data/samples/the-hollow-crown/storyweave.toml` (per-work
   config: file-mode chapter splitting, cruft patterns, a tuned `relex_rel_threshold`).
   These exist and are ingestible via the real CLI pipeline (`storyweave ingest` →
   `extract` → `relate` → `social` → `identity`), and SETUP_NOTES.md records that this
   real pipeline WAS run once, live, against them ("full ML pipeline (ingest, extract,
   relate) run on the real GLiNER models against the CC0 sample") — but that run used a
   throwaway DB, deleted after, not the committed demo DB.

2. **The actual committed/seeded demo** (`storyweave seed-demo`, `storyweave/demo/seed.py`
   → `seed_hollow_crown()`) does NOT run that pipeline at all. It hand-builds the graph
   directly through `Repository.add_node`/`add_edge`/`add_node_property` — 13 nodes (one
   of every ontology type), 11 Tier-1 edges, 2 Tier-3 identity edges (`SECRET_IDENTITY`@2,
   `ALIAS`@3, plus a `TRANSMIGRATED_INTO`@4 that deepens the same Wren/Caelum pair) and 3
   node properties. Chapter rows exist (4, ordinals 1–4) but their `clean_text` is a
   placeholder (`"[demo chapter N]"`) — the seeded demo's chapters carry NO real prose,
   only the graph. Its own module docstring is explicit about why: Tier-3 identity
   inference needs the LLM (off by default), so the committed slice "hand-builds ...
   mirroring the documented gold facts" instead of depending on a live LLM run.

3. **Provenance labeling, the load-bearing detail for Part B**: `seed_hollow_crown()`
   labels its hand-curated Tier-3 identity edges and the reveal-shifted node properties
   with `extraction_method=ExtractionMethod.LLM` — even though no LLM ever ran. The
   enum had only three values (`gliner`, `rule`, `llm`); `LLM` was used as a stand-in for
   "the kind of record the LLM layer would produce." **This conflicted with this phase's
   explicit instruction ("never label curated records as `llm`") — flagged to the user
   before writing any new data; resolved by adding a fourth enum value, `curated`.**
   Hollow Crown itself is UNCHANGED (still `llm`-labeled, per I2 — it stays
   byte-identical); only the new work's records use `curated`. See A1 decision log below.

**Seed command**: `storyweave seed-demo --db <path>` — schema init + `seed_hollow_crown()`
in one transaction-per-insert sequence (no batching). Raises if the slug already exists
("seed into a fresh --db file"). Zero ML, zero network, deterministic (same rows every
run — no randomness anywhere in `seed.py`).

**Decision log**: presented two options (match Hollow Crown's `llm` precedent for
consistency, vs. add a `curated` enum value for honesty). User chose to add
`ExtractionMethod.CURATED = "curated"`. Both demos now use internally-consistent but
*different* provenance conventions for their curated Tier-2/3 records, documented here so
a future reader isn't confused by the divergence.

### A2. How the app is served today

**MEASURED (this session), not assumed from old SETUP_NOTES claims — re-verified live:**

- **Two separate dev servers, no shared origin at the HTTP level.** `uvicorn
  storyweave.api.app:app --port 8000` (backend) and `npm run dev` (Vite, port 5173,
  frontend). `frontend/vite.config.ts` proxies `/api/*` to `http://127.0.0.1:8000` with
  `changeOrigin: true` — from the BROWSER's perspective everything is same-origin
  (`http://localhost:5173`), so the app never needs real CORS headers in dev.
- **`storyweave/api/app.py`'s `create_app()` has no `CORSMiddleware` and no static-file
  mount at all** — confirmed by reading the whole file. There is currently no way to
  serve the app from one FastAPI-owned origin; that's exactly Part C.1's job (`run.ps1`/
  `run.bat` + a static mount + SPA fallback for hash routes, added this phase).
- **API base URL**: hardcoded nowhere in the frontend beyond the Vite proxy and relative
  fetch paths (`/api/v1/...`) — `frontend/src/api.ts` and
  `frontend/src/codex/chapter/ChapterProvider.tsx` both fetch bare relative paths, so
  pointing the whole app at a single FastAPI-served origin later needs zero frontend
  code changes, only a build + a static mount.
- **Ingestion path, end to end, read from `storyweave/api/app.py`:**
  1. `POST /api/v1/works` (`IngestRequest{title, text}`) — validates non-empty
     title/text, slugifies the title, 409s if that slug already exists. Writes the raw
     text to a temp file, calls `ingest.pipeline.ingest()` **with `config=None`** (no
     `storyweave.toml` — pasted text has no config file to find), which cleans + splits
     + chunks + persists chapters/chunks with the DEFAULT `WorkConfig` (heading-regex
     chapter detection: `^\s*chapter\s+\d+\b`). 422s if zero chapters were detected.
  2. `jobs.start_analysis(slug, db_path)` (`api/jobs.py`) — a daemon thread that shells
     out to `.venv-ml/Scripts/python.exe -m storyweave.cli.main extract <slug> --db
     <path>`, then the same for `relate`, each a real subprocess (not an in-process
     import — the light API process never imports GLiNER). Path is
     `<repo>/.venv-ml/Scripts/python.exe` by default, overridable via
     `STORYWEAVE_ML_PYTHON`. A missing `.venv-ml` sets state `"error"` with a clear
     detail message rather than hanging; a subprocess timeout is 1200s per step; a
     non-zero return code captures the last 280 chars of stderr/stdout as the error
     detail.
  3. Frontend polls `GET /api/v1/works/{slug}/status` until `state == "ready"` (or
     `"error"`), then the reader can open the new work like any other.
  4. **There is no LLM/social/identity step in this path at all** — only `extract` then
     `relate` run, confirming the graph is usable off the GLiNER floor alone (rule 4)
     for anything ingested through the live UI. This is the exact path Part C.4 tests
     for real with a live ingest, not just read from source.

### A3. The 6 skipped pytest tests

**MEASURED**, `.venv\Scripts\python.exe -m pytest -q -rs`, quoted verbatim:

```
SKIPPED [1] tests\test_extract.py:63: could not import 'gliner': No module named 'gliner'
SKIPPED [1] tests\test_extract.py:71: could not import 'gliner': No module named 'gliner'
SKIPPED [1] tests\test_identity.py:532: live model not requested (set STORYWEAVE_LLM_LIVE=1 with a running runner)
SKIPPED [1] tests\test_relex.py:333: could not import 'gliner': No module named 'gliner'
SKIPPED [1] tests\test_search.py:140: could not import 'sentence_transformers': No module named 'sentence_transformers'
SKIPPED [1] tests\test_search.py:153: could not import 'chromadb': No module named 'chromadb'
```

All six are **by design**, not a gap: `.venv` (light) never installs GLiNER/
sentence-transformers/chromadb per the project's two-venv split (SPEC.md §4) — those
tests use `pytest.importorskip`, so the light gate (CI, this repo's normal `pytest` run)
skips them cleanly and `.venv-ml` (heavy) is where they'd actually run. The sixth
(`test_identity.py:532`) is a live-LLM integration test gated behind an explicit env var
(`STORYWEAVE_LLM_LIVE=1` + a running runner) — correctly skipped since I3 keeps the LLM
off entirely this phase.

**MEASURED**: `.venv-ml`'s python has `gliner`, `torch` (2.12.1+cpu, `cuda available:
False`), `sentence_transformers`, `chromadb` all importable — confirmed live this
session. `.venv-ml` does NOT have `pytest` installed (only the pinned ML runtime deps
from `requirements-ml.txt`), so these 6 tests were not re-run there; Part B.3's real
pipeline run (ingest → extract → relate on the new novel) is the actual exercise of that
code path this phase, measured directly rather than through pytest.

---

## Part B — A second demo novel

*(filled in as Part B proceeds)*

## Part C — End-to-end assimilation

*(filled in as Part C proceeds)*

## Known limits

*(filled in at close)*
