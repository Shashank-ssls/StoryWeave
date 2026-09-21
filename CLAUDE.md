# CLAUDE.md — standing rules for StoryWeave

> Claude Code reads this automatically each session.
>
> **CURRENT WORK: frontend redesign ("The Heretic's Codex") on branch `redesign/codex`.** For any frontend work, read `docs/design/FRONTEND_OVERHAUL.md` (execution rules + progress log) and `docs/design/DESIGN_SPEC.md` (what to build) BEFORE anything else. See "Frontend redesign" below.
>
> SPEC.md is the backend/system design (single source of truth for the engine); PROGRESS.md is the status of the ORIGINAL build (phases 0–9, all complete). At the start of every session, state which track you are on (redesign phase R0–R9) and what you are about to do, then proceed. Do not redo completed work.

## Context (important)
The original build (engine phases 0–9) is complete: backend, extraction pipeline, fence, demo tier and a Phase 8 frontend. The project was restored from a GitHub ZIP onto this machine; local setup is documented in `SETUP_NOTES.md` (use `dev.ps1` / `dev.bat`; all caches, venvs and models live inside the repo on F:, nothing on C:). SPEC.md is the ONE authoritative engine spec. The Phase 8 frontend and its `DESIGN.md` are SUPERSEDED by `docs/design/DESIGN_SPEC.md`.

## The five non-negotiable rules
1. **The graph models revealed reader-knowledge at chapter N, not world-truth.** Every node/edge/significant-property has a `revealed_chapter` and is invisible before it.
2. **The schema supports the full 8-type ontology and ALL identity relationships (SAME_AS, ALIAS, SECRET_IDENTITY, REINCARNATION, TRANSMIGRATED_INTO) from day one.**
3. **GLiNER-only extraction is the FLOOR and must yield a complete, useful graph by itself** (entities + Tier-1 structural relationships + fenced graph) with zero LLM.
4. **The LLM is a PURE ENHANCEMENT layer, never a dependency.** Run-order: local GPU → local CPU+RAM → Colab. Degrade gracefully to the GLiNER floor when unavailable.
5. **Local-first and free by default.** SQLite + vector store + models + frontend on local disk. No mandatory cloud/managed-DB/required keys. Optional opt-in LLM API path is OFF by default; with it off, zero runtime outbound calls.

## Backup discipline (CRITICAL — we lost everything once)
- After EVERY phase: commit, then **push to GitHub**. No phase is "done" until it's pushed.
- No Claude co-author trailer on any commit.
- Nothing installed globally; all dependencies, caches and browsers stay inside the repo (see SETUP_NOTES.md).

## Architecture rules
- SQLite is the source of truth; graph + vector index are rebuildable from it.
- ALL SQL lives in `db/repository.py`. One audit point.
- ALL spoiler filtering passes through `query/fence.py`, applied at the SQL/index level (never post-filtered), keying on `revealed_chapter`.
- Record provenance: extraction method (`gliner`|`rule`|`llm`) + evidence span on every entity/edge.
- Two-venv split: `.venv` (light app/CLI/tests) and `.venv-ml` (heavy NLP). ML imports are lazy; ML tests use `importorskip`.

## Ontology quick reference
- 8 node types: Character, Place, Organization, Item, Ability, Concept, Event, Title. (Species + Rank are SUBTYPES. Concept holds common-noun ideas: power systems, languages, named phenomena.)
- Relationships in 3 tiers: Tier 1 structural (GLiNER floor must produce), Tier 2 social (LLM adds), Tier 3 identity (LLM infers; schema exists day one).
- Every node/edge/property: `first_seen_chapter` (exists in text) + `revealed_chapter` (reader learns it). Fence keys on `revealed_chapter`.

## Workflow rules
- One phase at a time. Do not scaffold future phases early. Implement the requested phase, then STOP.
- End each phase green: pytest + ruff + mypy clean (+ frontend build and redesign checks where relevant).
- After each phase: interview-defense note (2–3 sentences) + the phase's acceptance-criteria result + update the relevant progress log + commit + push.
- Novel-specific knobs live in per-work config files (`storyweave.toml`), never in code. No `if work == "...":` anywhere.
- Small, reviewable diffs. Explain non-obvious decisions in comments and the phase summary. No black boxes — everything explainable in an interview.
- Ask before destructive actions: deleting data, DB files, demo outputs, backend code, or schema changes. (Exception: see redesign rule R4.)

## Frontend redesign (current track)
- **R1 Branch.** All redesign work happens on branch `redesign/codex`. `main` is the frozen, showable old version. Never commit to or merge into `main`; the user merges after R9.
- **R2 Phase naming.** Redesign phases are named **R0–R9** (they map to §3–§5 of FRONTEND_OVERHAUL.md, "Phase 0–9" there = R0–R9 here). They are unrelated to the engine phases in PROGRESS.md. Redesign progress is logged ONLY in FRONTEND_OVERHAUL.md §9, not in PROGRESS.md.
- **R3 Backend frozen.** No changes to Python, SQL, API routes or payload shapes during the redesign. Missing data → use the DESIGN_SPEC §13 fallback and log it. Backend pytest must stay 100% passing every phase.
- **R4 Deleting old frontend code is expected.** When a redesign phase replaces an old frontend component, delete the old component, its styles and its tests in the same phase and list them in the phase report. This does not require asking. Deleting anything outside `frontend/` still requires asking.
- **R5 Verification.** A UI phase is not green until it has been rendered in a real browser via the Playwright harness, screenshots inspected and compared to the artboards, and fence tests pass. Label every claim MEASURED / ASSERTED / BROKEN.
- **R6 Session log.** Every session appends an entry to `docs/design/SESSION_LOG.md` before its final commit, including sessions that stop mid-phase. A cold-start session reads the latest SESSION_LOG entry right after FRONTEND_OVERHAUL.md §9.

## Natural early-exit
Phases 0–5 (ontology + GLiNER + structural graph + fenced search + keystone fence) is a complete, fully-local, no-VRAM-risk product. (Historical note from the original build.)
