# PROGRESS — StoryWeave

> Live status. Resume cold from this file. Read with CLAUDE.md + SPEC.md each session.

## Current phase
**Phase 0 — Scaffold, schema, git, backup.** Status: **code complete & green; awaiting GitHub push** (no `gh` CLI on this machine — push commands handed to the user).

## Done
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

## In-progress / next
- **Blocking:** create the PRIVATE GitHub repo + push (commands in the Phase-0 handoff). No `gh` CLI here.
- After push: **Phase 1 — Ingestion & data model** (cleaner, splitter, offset-exact chunking, idempotent `storyweave ingest`, per-work `storyweave.toml`, CC0 sample novel).

## Known issues / TODOs
- Starlette TestClient emits a deprecation warning (httpx vs httpx2). Cosmetic; revisit if it becomes an error.
- `.venv-ml` intentionally not created yet (Phase 2 gate).

## Decisions log
- **Two-venv split confirmed working:** `.venv` = Python 3.14 (light); `.venv-ml` = Python 3.12 (heavy, Phase 2). Light deps installed cleanly on 3.14.
- **`config` as a module** (`config.py`), not a subpackage — simpler; satisfies the SPEC layout intent.
- **Ontology vocabulary lives in `db/models.py`** and is reused to build SQL CHECK constraints in `repository.py`, so SQL and pydantic mirrors cannot drift.
- **`requires-python = ">=3.12"`**, ruff/mypy target `py312` — the floor shared by both venvs.
- Health route under `/api/v1` from the start (forward-compatible with Phase 6 routes).
- No Claude co-author trailer on commits (CLAUDE.md backup discipline).
