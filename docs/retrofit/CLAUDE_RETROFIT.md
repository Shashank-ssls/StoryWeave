# CLAUDE.md — RETROFIT TRACK (paste this block at the TOP of CLAUDE.md in Phase R0)

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
