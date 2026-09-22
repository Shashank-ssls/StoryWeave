# CLAUDE.md — standing rules for StoryWeave

> Claude Code reads this automatically each session.
>
> **CURRENT WORK: integration phase (frontend ↔ backend assimilation + a demo-scale second novel) on branch `integration/demo-scale`.** Read `docs/INTEGRATION.md` (recon + measured numbers + progress) BEFORE anything else for this track. See "Integration phase" below.
>
> The frontend redesign (R0–R9, "The Heretic's Codex") is COMPLETE and merged into `main` — see "Frontend redesign (complete)" below and `docs/design/FRONTEND_OVERHAUL.md` §9 for its full history. `docs/design/DESIGN_SPEC.md` is still the live reference for frontend visual/behavioural rules.
>
> SPEC.md is the backend/system design (single source of truth for the engine); PROGRESS.md is the status of the ORIGINAL build (phases 0–9, all complete). At the start of every session, state which track you are on and what you are about to do, then proceed. Do not redo completed work.

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

## Frontend redesign (complete)
R0–R9 ("The Heretic's Codex") shipped and is merged into `main`. These rules governed
that track and stay here for reference — the branch is gone, but the discipline they
describe (visual verification protocol, honesty labels, session-log habit) still applies
wherever frontend work happens.
- **R1 Branch (historical).** Redesign work happened on branch `redesign/codex`, merged
  into `main` at the end of R9.
- **R2 Phase naming.** Redesign phases were named **R0–R9** (map to §3–§5 of
  FRONTEND_OVERHAUL.md). Unrelated to the engine phases in PROGRESS.md. Redesign history
  lives in FRONTEND_OVERHAUL.md §9, not PROGRESS.md.
- **R3 Backend frozen (superseded — see "Integration phase" below).** During the
  redesign, backend Python/SQL/API/payload shapes were off-limits. That freeze is lifted
  for the current integration track, narrowly, per the rules below.
- **R4 Deleting old frontend code is expected** when a replacement lands in the same
  phase — still the operating default for frontend work generally.
- **R5 Verification.** No UI change is green until rendered in a real browser via the
  Playwright harness, screenshots inspected, fence tests passing. Label every claim
  MEASURED / ASSERTED / BROKEN. Still binding for all frontend work, redesign or not.
- **R6 Session log.** `docs/design/SESSION_LOG.md` was the redesign's session log.

## Integration phase (current track)
Full frontend ↔ backend assimilation, plus a second, demo-scale (~40 chapter) novel to
exercise the app at real scale (cast overflow, arcs, the chapter picker). Branch
`integration/demo-scale`, off `main` (which now has the merged redesign).
- **I1 Backend unfrozen, narrowly.** Unlike the redesign, backend Python/SQL/API changes
  ARE allowed this phase, but only for what the phase actually needs (arcs storage +
  fenced endpoint, the new `ExtractionMethod.CURATED` provenance value, one-origin static
  serving, and fixes required to make the existing ingestion path actually work end to
  end). All standing architecture rules still bind without exception: every SQL statement
  in `db/repository.py`, every spoiler filter through `query/fence.py` at the SQL level,
  provenance + evidence span on every entity/edge, per-work knobs in `storyweave.toml`
  only (never `if work == "...":`).
- **I2 Hollow Crown is untouchable.** Its seeded data, fixtures, and every existing test
  must keep passing UNCHANGED — it is the fence's own proof and the redesign's entire
  regression suite depends on it byte-for-byte.
- **I3 No LLM.** Nothing about Ollama or the LLM tiers gets installed, enabled, or
  required. `llm_enabled` stays `False`. Tier-2/Tier-3 records the LLM would normally
  produce are hand-curated from a written "bible," provenance-tagged `curated` (never
  `llm` — that would misrepresent how the data was actually produced).
- **I4 Honesty labels, verbatim evidence.** Every claim MEASURED / ASSERTED / BROKEN.
  Quote runner summary lines verbatim in reports, not paraphrases. Never run test suites
  in parallel. No scheduled wakeups or loops during this phase.
- **I5 Progress log.** Integration progress lives in `docs/INTEGRATION.md`, with a
  consolidated report added to `docs/design/FRONTEND_OVERHAUL.md` §9 at the end and a
  `docs/design/SESSION_LOG.md` entry every session (same session-log habit as R6).
- **I6 No merge to main.** Same discipline as the redesign: work stays on
  `integration/demo-scale` until the user reviews and merges it themselves.

## Natural early-exit
Phases 0–5 (ontology + GLiNER + structural graph + fenced search + keystone fence) is a complete, fully-local, no-VRAM-risk product. (Historical note from the original build.)
