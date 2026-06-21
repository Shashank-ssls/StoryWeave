# CLAUDE.md — standing rules for StoryWeave

> Claude Code reads this automatically each session. SPEC.md is the full design (single source of truth); PROGRESS.md is live status. Read CLAUDE.md, SPEC.md, and PROGRESS.md at the start of every session, state which phase we're on and what you're about to do, then proceed. Do not redo completed work — trust PROGRESS.md.

## Context (important)
This is a from-scratch build. A previous version existed but was lost with no backup. SPEC.md is the ONE authoritative spec (infrastructure + 8-type ontology + GLiNER + the universal reveal fence all merged). There is no separate v2 file.

## The five non-negotiable rules
1. **The graph models revealed reader-knowledge at chapter N, not world-truth.** Every node/edge/significant-property has a `revealed_chapter` and is invisible before it.
2. **The schema supports the full 8-type ontology and ALL identity relationships (SAME_AS, ALIAS, SECRET_IDENTITY, REINCARNATION, TRANSMIGRATED_INTO) from day one.**
3. **GLiNER-only extraction is the FLOOR and must yield a complete, useful graph by itself** (entities + Tier-1 structural relationships + fenced graph) with zero LLM.
4. **The LLM is a PURE ENHANCEMENT layer, never a dependency.** Run-order: local GPU → local CPU+RAM → Colab. Degrade gracefully to the GLiNER floor when unavailable.
5. **Local-first and free by default.** SQLite + vector store + models + frontend on local disk. No mandatory cloud/managed-DB/required keys. Optional opt-in LLM API path is OFF by default; with it off, zero runtime outbound calls.

## Backup discipline (CRITICAL — we lost everything once)
- git is initialized in Phase 0, with a private GitHub remote.
- After EVERY phase: commit, then **push to GitHub**. No phase is "done" until it's pushed.
- No Claude co-author trailer on any commit.

## Architecture rules
- SQLite is the source of truth; graph + vector index are rebuildable from it.
- ALL SQL lives in `db/repository.py`. One audit point.
- ALL spoiler filtering passes through `query/fence.py`, applied at the SQL/index level (never post-filtered), keying on `revealed_chapter`.
- Record provenance: extraction method (`gliner`|`rule`|`llm`) + evidence span on every entity/edge.
- Two-venv split: `.venv` (3.14, light app/CLI/tests) and `.venv-ml` (3.12, heavy NLP). ML imports are lazy; ML tests use `importorskip`.

## Ontology quick reference
- 8 node types: Character, Place, Organization, Item, Ability, Concept, Event, Title. (Species + Rank are SUBTYPES. Concept holds common-noun ideas: power systems, languages, named phenomena.)
- Relationships in 3 tiers: Tier 1 structural (GLiNER floor must produce), Tier 2 social (LLM adds), Tier 3 identity (LLM infers; schema exists day one).
- Every node/edge/property: `first_seen_chapter` (exists in text) + `revealed_chapter` (reader learns it). Fence keys on `revealed_chapter`.

## Workflow rules
- One phase at a time (0 → 9). Do not scaffold future phases early. Implement the requested phase, then STOP.
- End each phase green: pytest + ruff + mypy clean (+ frontend build where relevant).
- After each phase: interview-defense note (2–3 sentences) + the phase's acceptance-criteria result + update PROGRESS.md + commit + push.
- Extraction quality is fixed and PROVEN before the ontology-dependent frontend work. Never polish a graph whose data is still wrong — the frontend is Phase 8, last, on purpose.
- Gates mirror discipline: Phase 2 proves GLiNER installs/runs before building on it; Phase 7 runs an LLM GPU→CPU→Colab go/no-go test before building on it.
- Novel-specific knobs live in per-work config files (`storyweave.toml`), never in code. No `if work == "...":` anywhere.
- Small, reviewable diffs. Explain non-obvious decisions in comments and the phase summary. No black boxes — everything explainable in an interview.
- Ask before destructive actions (deleting files, large rewrites, schema changes after Phase 0).

## PROGRESS.md
Create it in Phase 0 and update at the end of every phase. Keep it short and factual: current phase + status, Done list, In-progress/next, Known issues/TODOs, Decisions log (with measured numbers as they arrive). The next session must be able to resume cold from it.

## Natural early-exit
Phases 0–5 (ontology + GLiNER + structural graph + fenced search + keystone fence) is a complete, fully-local, no-VRAM-risk product. Reassess appetite at the end of Phase 5 before the LLM layer (Phase 7) and the frontend/packaging push.
