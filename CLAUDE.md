# RETROFIT TRACK — read this first

> **CURRENT WORK: v2 retrofit into v1, branch `retrofit/v2-core`.**
> Phase prompts live in `docs/retrofit/R0_*.md` … `R8_*.md`. Progress log:
> `docs/retrofit/RETROFIT_PROGRESS.md`. At the start of every session, state which
> phase (R0–R8) you are on and what you are about to do. Do not redo completed
> phases. Do not start the next phase until the current one is green, committed
> and pushed.

## Why this track exists (one paragraph)
v1 was measured (`evidence/EVAL_V1.md`, `evidence/errors_v1.md`, `evidence/REPORT.md`
— the planning chat's `FINDINGS.md` was never committed and is not a source here). Fence: 0 leaks / 105,243
elements. Relation micro-F1: 0.046 — 160 of 162 false positives came from the
Tier-1 co-occurrence rule. 8 node types caused 16 of 44 entity errors (type
disagreement). The cast filter was a client-side no-op. At ch40 the graph served
206 nodes / 1,316 edges and was unreadable to a non-technical reviewer. The
retrofit applies the v2 fixes that these measurements blame, inside the v1
codebase, and cuts everything else (timeline, events, death subsystem,
backbone filter, coref, ONNX) to later work.

## Rules that SUPERSEDE the old "five non-negotiable rules"
1. **Fence first, always.** `revealed_chapter <= :n` is the first WHERE clause of
   every payload query and lives only in `query/fence.py` → `db/repository.py`.
   It is a SAFETY filter. Display filters (cast size, node types, grade) are
   separate, visibly distinct clauses. Never merge them.
2. **Four node types:** Character, Organization, Place, Item. Default graph =
   Characters only. Ability / Concept / Event / Title are never drawn.
3. **Twelve relations, closed list:** KIN_OF, ROMANTIC_WITH, ALLY_OF, ENEMY_OF,
   SERVES, MENTOR_OF, KILLED, SAME_AS (ring 1) · MEMBER_OF, LEADS, OWNS,
   LOCATED_IN (ring 2, overlays only). Anything else is rejected in code.
4. **Citation or nothing.** Every edge has a verbatim quote from clean text.
   Shipped edges are grade STATED: the quote contains BOTH participant names
   (or an alias of each) and the relation cue.
5. **No co-occurrence edges in the default graph.** The rule builder stays in
   the repo behind `relations.cooccurrence_enabled = false` for before/after
   evidence only.
6. **No client-side filtering of any kind.** The client renders what it receives.
7. **No future information in display filters.** Importance rank at chapter n is
   computed only from chapters ≤ n (a book-wide rank is a spoiler side channel).
8. **The LLM proposes, the code disposes.** LLM output passes the validator or is
   discarded with a logged reason. With no LLM available, the system still works.
9. **Measured vs asserted.** Every number written anywhere is labelled
   [MEASURED], [PREDICTED] or [PROJECTED]. Never write a projection as a result.
   A zero is reported with its tested surface.
10. **Rule Zero (frontend):** screenshot and inspect your own UI output before
    declaring any frontend step green.

### Amendment to rule 4 (R7, user-approved 2026-09-29) — served grades

Rule 4 said shipped edges are grade STATED. **It now reads: the graph serves STATED and
INFERRED edges.** Stored-and-rejected proposals are still never served, and every served
edge still carries its verbatim quote. Three guards come with the change:

1. **`SAME_AS` is served only when STATED.** An identity claim is the most damaging thing
   to get wrong, so the identity family keeps the strict rule.
2. **The grade is a DISPLAY clause, applied after the fence**, exactly like cast size and
   node types. It is not a fence change and must never be merged into the fence clause
   (retrofit rule 1).
3. **INFERRED is visibly different** in the UI: dashed line, label suffixed "(implied)".

**The measured cost, from `evidence/retrofit/R5_RESULT.md` §3** — this amendment is a
priced decision, not a preference:

| pooled `cumulative`, 12-relation key | TP | FP |
| --- | ---: | ---: |
| STATED only | 0 | 10 |
| STATED + INFERRED | **1** | **25** |

So admitting INFERRED buys one true positive and costs fifteen additional false positives.
It is accepted because the alternative measured worse as a product: at chapter 40 the
STATED-only default view is **1 edge across 20 characters** (R5 §4), which R4c's
screenshots showed reads as a broken app rather than a sparse one. The dashed styling is
what keeps the weaker evidence honest on screen.

## Local-only environment (HARD RULE — nothing on C:)
Every download, cache, model, browser, temp file and tool install stays inside
the repo on F:. Before ANY install, download, model pull or pipeline run:
1. Activate through `.\dev.ps1` (light) or `.\dev.ps1 -Ml` (ML). Never use a
   bare `python`, `pip` or `npm` from a shell that did not run it.
2. Run `python tools/check_local_env.py`. If it fails, STOP and report. Do not
   work around it.

Where things go (all under `<repo>\.local\` unless noted):
| What | Variable | Location |
|---|---|---|
| pip cache | `PIP_CACHE_DIR` | `.local\pip_cache` |
| HuggingFace models (GLiNER, relex) | `HF_HOME` | `F:\Dev\shared\hf-cache` (existing machine-wide cache on F:, outside the repo; keep, do not move or re-download) |
| torch cache | `TORCH_HOME` | `.local\torch_cache` |
| npm cache | `npm_config_cache` | `.local\npm_cache` |
| Playwright browsers | `PLAYWRIGHT_BROWSERS_PATH` | `.local\ms-playwright` |
| Ollama models | `OLLAMA_MODELS` | `.local\ollama_models` |
| Temp files (pip builds, torch unpack) | `TEMP`, `TMP` | `.local\tmp` |
| LLM response cache | config | `.local\llm_cache` |

Forbidden: `pip install --user`, `pip install` outside a venv, `npm install -g`,
`npx` of anything not in `frontend/package.json`, `playwright install` without
the variable set, `ollama pull` without `OLLAMA_MODELS` set, `winget`/`choco`/
system installers, and changing system or user environment variables. All
variables are set per session by `dev.ps1` / `dev.bat` only.

**Any write to C: (file, registry, PATH, shortcut, service) must be recorded in
`docs/retrofit/C_DRIVE_LEDGER.md` in the same session, before the phase is committed.**
A third-party installer can add a registry key, a Start Menu shortcut and a user PATH
entry without any project code running — that is what Ollama 0.34.4 did on 2026-09-29
(ledger §2). `tools/uninstall_project_c_traces.ps1` removes only ledger items, dry-run
by default.

New Python packages go into the correct venv's `requirements*.txt` and lock file
in the same commit. Prefer what is already installed (stdlib `urllib` for Ollama
HTTP, existing `matplotlib` if present) over adding packages.

## Unchanged rules (still in force)
- SQLite is the source of truth. ALL SQL lives in `db/repository.py`.
- Two venvs (`.venv`, `.venv-ml`); ML imports lazy; nothing global; all caches on F:.
- Novel-specific knobs in `storyweave.toml`, never `if work == ...`.
- Commit + push after every phase. No Claude co-author trailer.
- End every phase: pytest + ruff + mypy clean (+ `npm run build` for frontend).
- After each phase: 2–3 sentence viva-defense note, acceptance checklist with
  pass/fail, update `RETROFIT_PROGRESS.md`, commit, push, STOP.

## Frozen artifacts — never modify
`evidence/v1_ninth_house.db`, `evidence/EVAL_V1.md`, `evidence/BASELINE.md`,
`evidence/annotation/*.json`, `PREDICTIONS.md`. New results go in
`evidence/retrofit/`.

---

# CLAUDE.md — standing rules for StoryWeave (pre-retrofit; still in force except where the retrofit block above conflicts)

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

> Superseded by the retrofit rules above where they conflict (rules 2 and 3).

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
