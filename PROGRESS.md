# PROGRESS — StoryWeave

> Live status. Resume cold from this file. Read with CLAUDE.md + SPEC.md each session.

## Current phase
**Phase 2 — GLiNER entity extraction (the floor).** Status: **DONE & green; ready to push.** Environment gate passed (`.venv-ml` 3.12 + GLiNER + torch, model cache on F:). Next: Phase 3 (Tier-1 relationships + graph projection).

## Done (Phase 2)
- **Environment gate PASSED.** `.venv-ml` (Python 3.12) created; installed `torch==2.12.1+cpu`, `gliner==0.2.27`, `transformers==5.6.2`, `huggingface_hub==1.20.1`; real smoke extraction works on CPU (Wren→Character 0.98, Aldercross→Place, Coil→Organization). Versions pinned in `requirements-ml.txt`.
- **Model cache forced onto F:** (off C:, env discipline). `config.hf_home` → `<repo>/.hf-cache` (gitignored), applied via `nlp.extractor.configure_hf_cache` before any HF import; `tests/conftest.py` pins it before `importorskip` triggers HF; `HF_HUB_DISABLE_SYMLINKS=1` avoids WinError 1314. Verified: weights land on F:, C: stays clean. (Two C: leaks during setup were detected and deleted.)
- `nlp/labels.py`: GLiNER prompt labels → canonical 8-type map (incl. Concept-boosting prompts: "power system", "phenomenon", "language").
- `nlp/extractor.py`: lazy GLiNER wrapper (`GlinerExtractor`), returns canonical-typed `MentionSpan`s; ML imports lazy so it imports in the light venv.
- `nlp/cluster.py`: pure-Python alias clustering — normalize (case/article/punct), majority-vote type, conservative token-subset merge ("Veris"→"Lady Veris", "Coil"→"the Coil"). Canonical entity carries `first_seen_chapter`. Deliberately NOT semantic identity (that's Tier-3/Phase 7).
- `nlp/metrics.py`: pure P/R/F1 (generic, per-type + micro ALL).
- `nlp/pipeline.py`: `extract_work` — clear→GLiNER per chunk (offsets mapped to chapter)→persist raw mentions→cluster→insert canonical nodes (method=gliner, evidence quote, importance=mention count)→backfill `mention.node_id`. Idempotent (derived data, clear+rebuild).
- `db`: `mentions` table (raw candidates, persisted BEFORE clustering, FK + node_id backfill) + `Mention` model + repo methods (`add/list/count/clear_mention`, `set_mention_node`, `list/count/clear_nodes`).
- `cli`: `storyweave extract <slug> [--config --model --threshold --device --db]` (lazy ML imports).
- `eval/ner_eval.py` + `data/labels/the-hollow-crown_ch01.json`: hand-labeled ch01 (incl. a Concept entity, "the Glasswound"). Ran: **Concept P/R/F1 = 1.00**, Place correct, ALL F1=0.53 (gold 8, pred 15). Sample ch01 gained a named phenomenon "the Glasswound" so the corpus genuinely exercises the Concept type.
- Tests: +15 (cluster, metrics, mentions repo round-trip — pure/light) and 2 ML-gated GLiNER tests (`importorskip`). Light venv: 33 passed, 2 skipped. `.venv-ml`: the 2 GLiNER tests pass.

## Done (Phase 1)
- `ingest/cleaner.py`: NFKC, line-ending normalize, de-hyphenate soft wraps, config-driven cruft stripping (logged, not silently dropped), paragraph-preserving re-flow (blank-line or single-newline mode). Returns `CleanResult(text, removed_lines)`.
- `ingest/splitter.py`: chapter detection (`auto`/`file`/`heading`/`delimiter`; dir = one file per chapter, leading heading line → title); sentence spans (ASCII + CJK terminators); `chunk_spans` (max_chars, sentence overlap, oversize sentence = own chunk); `chunk_chapter` builds chunks by **slicing** clean_text so the offset invariant holds structurally.
- `ingest/work_config.py`: `storyweave.toml` loader via `tomllib` → validated `WorkConfig` (cleaning/splitting/chunking). Absent file = all defaults. `find_work_config` auto-detects beside file / in dir.
- `ingest/pipeline.py`: orchestrates config→clean→split→chunk→repo; idempotent (chapter keyed by (work, ordinal) + content_hash; identical = skip, changed = replace+rechunk); returns `IngestReport`.
- `db/repository.py`: added `chapters` + `chunks` tables (FK cascade, UNIQUE constraints) and methods (`get_or_create_work`, chapter/chunk CRUD + counts). All SQL still in repository.
- `db/models.py`: `Chapter` + `Chunk` pydantic mirrors (source-data layer, no reveal stamps; content_hash for idempotency).
- `cli/main.py`: `storyweave ingest <path> [--title --slug --config --db]` (lazy ML-free imports).
- **CC0 sample novel** `data/samples/the-hollow-crown/` (4 chapters + `storyweave.toml` + `LICENSE.md`): alias-rich, with a secret royal heir (Wren = Prince Caelum), a spymistress alias (Gray Sparrow = Lady Veris), and a transmigration hint — stresses Phase 2/5/7. Real novels stay in gitignored `data/raw/`.
- Tests (15 new, all green): cleaner (NFKC/dehyphen/cruft/paragraph modes), splitter (sentence spans, chunk sizing, heading+delimiter detection, **offset round-trip invariant**), end-to-end ingest of sample incl. **double-ingest-no-duplicates** + persisted-chunk offset invariant.

## Done (Phase 0)
- Package scaffold: `storyweave/{config,db,ingest,nlp,graph,search,query,api,cli}` + `frontend/ eval/ tests/ data/{raw,samples,labels}/ docker/`.
- `pyproject.toml`: light deps (fastapi, uvicorn, pydantic, pydantic-settings, typer) + `[dev]` (pytest, httpx, ruff, mypy). ruff + mypy(strict) + pytest config. Console script `storyweave`.
- `requirements-ml.txt`: documents the intended `.venv-ml` (Python 3.12) setup — **not installed** (Phase 2 is the gate).
- `.gitignore` (excludes `.venv/ .venv-ml/ *.sqlite node_modules/ data/raw/`), `.env.example` (LLM off by default).
- `storyweave/config.py`: pydantic-settings, env prefix `STORYWEAVE_`, `llm_enabled=False` default.
- `storyweave/api/app.py`: FastAPI app, `GET /api/v1/health`.
- `storyweave/cli/main.py`: Typer CLI with `version` + `info` commands.
- **Full 8-type schema, day one** — `db/models.py` (pydantic mirrors + ontology vocab) and `db/repository.py` (ALL SQL; 8 node types w/ CHECK, nullable subtype, 3-tier edges w/ CHECK, node-property mechanism, universal `first_seen_chapter`+`revealed_chapter` + provenance on every row).
- Tests (9, green): smoke (version + LLM-off default), `/health`, schema round-trip incl. Tier-3 identity edge + property-level reveal + CHECK-constraint rejection.
- `.venv` (Python 3.14) created; `pip install -e ".[dev]"` succeeded. README outline.

## Gate result (Phase 1)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, no issues in 25 source files.
- `pytest` → 24 passed.
- CLI verified: `storyweave ingest data/samples/the-hollow-crown` → `+4 chapters, +12 chunks, 2 cruft lines removed`; re-run → `0 added, 4 unchanged, 0 chunks` (idempotent).

## Gate result (Phase 0)
- Package scaffold: `storyweave/{config,db,ingest,nlp,graph,search,query,api,cli}` + `frontend/ eval/ tests/ data/{raw,samples,labels}/ docker/`.
- `pyproject.toml`: light deps (fastapi, uvicorn, pydantic, pydantic-settings, typer) + `[dev]` (pytest, httpx, ruff, mypy). ruff + mypy(strict) + pytest config. Console script `storyweave`.
- `requirements-ml.txt`: documents the intended `.venv-ml` (Python 3.12) setup — **not installed** (Phase 2 is the gate).
- `.gitignore` (excludes `.venv/ .venv-ml/ *.sqlite node_modules/ data/raw/`), `.env.example` (LLM off by default).
- `storyweave/config.py`: pydantic-settings, env prefix `STORYWEAVE_`, `llm_enabled=False` default.
- `storyweave/api/app.py`: FastAPI app, `GET /api/v1/health`.
- `storyweave/cli/main.py`: Typer CLI with `version` + `info` commands.
- **Full 8-type schema, day one** — `db/models.py` (pydantic mirrors + ontology vocab) and `db/repository.py` (ALL SQL; 8 node types w/ CHECK, nullable subtype, 3-tier edges w/ CHECK, node-property mechanism, universal `first_seen_chapter`+`revealed_chapter` + provenance on every row).
- Tests (9, green): smoke (version + LLM-off default), `/health`, schema round-trip incl. Tier-3 identity edge + property-level reveal + CHECK-constraint rejection.
- `.venv` (Python 3.14) created; `pip install -e ".[dev]"` succeeded. README outline.

## Gate result (Phase 0)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, no issues in 18 source files.
- `pytest` → 9 passed.
- `storyweave version` → `0.1.0`; `storyweave info` → `llm_enabled: False`.

## Gate result (Phase 2)
- `ruff check .` → All checks passed.
- `mypy` (strict) → Success, 34 source files.
- `pytest` (light `.venv`) → 33 passed, 2 skipped (GLiNER tests skip without ML).
- `pytest` (`.venv-ml`) → GLiNER tests pass; cache stays on F:, C: clean.
- `eval/ner_eval.py` → real per-type P/R/F1 (Concept 1.00, ALL F1 0.53).
- CLI: `storyweave extract the-hollow-crown` → 89 mentions → 38 entities (7/8 types); re-run identical (idempotent).

## In-progress / next
- **Phase 3 — Tier-1 relationships + graph projection.** Structural relations (Tier-1 list + RelatedTo fallback) via proximity/rules over canonical entities, with method+evidence+reveal stamps; `graph/builder.py` (SQLite→NetworkX, fenced by N) + `graph/serialize.py` (→Cytoscape JSON). Edge visible only if both endpoints visible at N.

## Known issues / TODOs
- Starlette TestClient emits a deprecation warning (httpx vs httpx2). Cosmetic; revisit if it becomes an error.
- `.venv-ml` intentionally not created yet (Phase 2 gate).
- Dir-mode chapter detection ingests every `*.txt`; non-chapter files in a sample dir must use another extension (the sample's notice is `LICENSE.md`). Acceptable for now.

## Decisions log
- **Two-venv split confirmed working:** `.venv` = Python 3.14 (light); `.venv-ml` = Python 3.12 (heavy, Phase 2). Light deps installed cleanly on 3.14.
- **`config` as a module** (`config.py`), not a subpackage — simpler; satisfies the SPEC layout intent.
- **Ontology vocabulary lives in `db/models.py`** and is reused to build SQL CHECK constraints in `repository.py`, so SQL and pydantic mirrors cannot drift.
- **`requires-python = ">=3.12"`**, ruff/mypy target `py312` — the floor shared by both venvs.
- Health route under `/api/v1` from the start (forward-compatible with Phase 6 routes).
- No Claude co-author trailer on commits (CLAUDE.md backup discipline).
- **Phase 1:** chunk offset invariant is guaranteed *structurally* by slicing `clean_text[start:end]` (not by reconstructing text), so it holds regardless of sentence-splitter quality.
- **Phase 1:** chapters/chunks carry NO reveal stamps — they are raw source data; the reveal mechanism is reserved for graph elements (nodes/edges/properties).
- **Phase 1:** idempotency keyed on (work, ordinal) + content_hash of clean_text; identical re-ingest skips, changed content replaces chapter (chunks cascade) and re-chunks.
- **Phase 1:** cleaning is paragraph-preserving and defines the canonical coordinate space that chunk offsets index into.
- **Phase 2 (HF cache on F:):** model weights cache at `<repo>/.hf-cache` (gitignored), pinned via `config.hf_home` + `configure_hf_cache` + `tests/conftest.py`, with `HF_HUB_DISABLE_SYMLINKS=1`. Both GLiNER now and the Phase-7 LLM cache on F:, never C:. Exact path: `F:\Dev\Claude_folder_project_and_stuff\storyweave\.hf-cache`. (HF binds the cache path at IMPORT time, so the env var must be set before the first `huggingface_hub` import — hence conftest.)
- **Phase 2 (model):** `urchade/gliner_small-v2.1` on CPU is the pinned floor; small model also fits the 4 GB GPU via `gliner_device="cuda"`.
- **Phase 2 (clustering):** string-based canonicalization only (surface variants), NOT semantic identity — Wren≠Caelum here on purpose; identity is Tier-3, fenced, Phase 7.
- **Phase 2 (extraction idempotency):** mentions+nodes are derived; a re-run clears and rebuilds (no dup nodes).
- **Phase 2 (sample):** ch01 gained a named phenomenon "the Glasswound" so the CC0 corpus exercises the signature Concept type (GLiNER tags it Concept ~0.45, above the 0.4 threshold).
