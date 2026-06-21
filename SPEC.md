# StoryWeave — SPEC (authoritative, single source of truth)
### A spoiler-aware knowledge engine for web novels

> **Status:** fresh from-scratch build. A previous version existed but was lost with no backup. This document is the ONE authoritative spec — it folds in everything (infrastructure + the 8-type ontology + GLiNER extraction + the universal reveal fence). There is no separate v2 file; this is the whole design. `CLAUDE.md` holds the standing rules; `PROGRESS.md` (created in Phase 0) tracks live status.
>
> **How to use with Claude Code:** Build ONE phase at a time (0 → 9). Each phase ends green (pytest + ruff + mypy + frontend build where relevant), is committed, and is **pushed to the private GitHub remote** before the next begins. After each phase, output an interview-defense note (2–3 sentences) and the phase's acceptance-criteria result. Read CLAUDE.md, SPEC.md, and PROGRESS.md at the start of every session.

---

## 1. What StoryWeave is (one paragraph)

StoryWeave ingests web-novel chapters and builds a **living knowledge graph** of the story — characters, places, organizations, items, abilities, concepts, events, and titles as nodes; typed relationships as edges — plus a **spoiler-aware semantic search**. The defining principle: **the graph models what the reader has been told by chapter N, not objective world-truth.** Every node, edge, and significant property carries a reveal point and is invisible until the story discloses it. A chapter slider drives this reading position, and the graph blooms as the reader advances. Extraction uses **GLiNER** (zero-shot, genre-agnostic, free, local) as the floor, with an **optional local LLM** enhancement layer for the reasoning GLiNER can't do (social relationships, context disambiguation, identity inference). The system runs **fully local and offline by default**; the LLM is an enhancement, never a dependency.

---

## 2. The five non-negotiable rules

1. **The graph models revealed reader-knowledge at chapter N, not world-truth.** Every node, edge, and significant property has a `revealed_chapter` and is invisible before it.
2. **The schema supports the full 8-type ontology and ALL identity-relationship types (SAME_AS, ALIAS, SECRET_IDENTITY, REINCARNATION, TRANSMIGRATED_INTO) from day one.**
3. **GLiNER-only extraction is the FLOOR and must yield a complete, useful graph by itself** — entities, structural relationships, and the fenced graph all function with zero LLM.
4. **The LLM is a PURE ENHANCEMENT layer, never a dependency.** Run-order fallback: local GPU → local CPU+RAM → Colab. The pipeline degrades gracefully to the GLiNER floor whenever the LLM is unavailable.
5. **Local-first and free by default.** SQLite, vector store, models, and frontend all live on local disk. No mandatory cloud, no managed database, no required API keys. The only runtime network is an *optional* opt-in LLM API path (off by default) — with it off, zero outbound calls at runtime.

---

## 3. Builder context & compute

- Solo developer, final-year Data Science student. Strong: Python, pandas, scikit-learn, basic PyTorch, ML fundamentals. Learning: production backend patterns, async, frontend state. Explain those while building.
- This is a flagship resume project — must be impressive, genuinely useful, and **fully defensible in an interview** (no black boxes; everything explainable).
- **Hardware:** Ryzen 5 4600H (6-core CPU), 16 GB system RAM, GTX 1650 (4 GB VRAM). The 16 GB RAM is the safety net for the LLM step — small quantized models run on CPU when VRAM is too tight. GLiNER runs fine locally (GPU or CPU).
- **Environment discipline:** dependencies off the C: drive; always a virtual environment. Windows host — prefer cross-platform paths; note WSL/Colab alternatives where a step is POSIX-only.
- **Backup discipline (CRITICAL, learned the hard way):** git from Phase 0, pushed to a private GitHub remote after every phase. A deleted folder must never again lose work.

---

## 4. The two-environment architecture

Python 3.14 is the only interpreter that may be pre-installed; spaCy/torch/GLiNER historically lack 3.14 wheels. Therefore:
- **`.venv` (Python 3.14):** the light app — FastAPI, CLI, pydantic, the fast test/lint/type gate. No heavy ML deps. ML modules import lazily so the package still imports here.
- **`.venv-ml` (Python 3.12):** the heavy NLP — GLiNER, torch, sentence-transformers, the LLM layer, the vector-store backends. The app that actually serves search/graph runs here; the CLI pipeline steps run here.

This split is a deliberate, documented decision. Tests needing ML use `importorskip` so the light gate skips them and the ML venv runs them.

---

## 5. The universal ontology

### 5.1 Node types — exactly EIGHT
`Character` · `Place` · `Organization` · `Item` · `Ability` · `Concept` · `Event` · `Title`

Principle: **compact core, rich edges.** A small fixed label set keeps GLiNER accurate; richness comes from subtypes, properties, and relationships — not more node types.

- **`Concept`** is the home for load-bearing *common-noun* ideas that proper-noun NER can't see: power systems, languages, named phenomena ("the Nightmare Spell," "Aspect," "the Dream Realm," "Beyonder," "the Hermes language"). This is the biggest qualitative win in the design — without it the graph is a hollow list of names.
- **Species and Rank are SUBTYPES, not node types** (low-volume, easily confused by zero-shot models; a wrong guess becomes a minor mislabel rather than a phantom node type).

### 5.2 Subtypes (a node property; null is always valid)
- **Organization** → Faction, Clan, Sect, Guild, Kingdom, Empire, Army, Cult, Church, Corporation, School
- **Ability** → Spell, Technique, Skill, Aspect, Talent, Passive, Active
- **Item** → Weapon, Consumable, Resource, Treasure, Relic, Artifact
- **Concept** → System, PowerSystem, Language, Species, Rank, Currency, Law, Phenomenon
- **Character** → Person, Deity, Creature, Construct
- **Place** → Region, City, Realm, Building, Landmark
- **Event** → Battle, Tournament, Disaster, Ritual, Ceremony
- **Title** → Honorary, Political, Religious, Combat

### 5.3 Relationship vocabulary — THREE tiers, matched to what each layer can deliver
- **Tier 1 — GLiNER floor MUST produce (structural):** `AffiliatedWith`, `LocatedIn`, `MemberOf`, `LeaderOf`, `HasAbility`, `OwnsItem`, `HasTitle`, `ParticipatedIn`, + generic `RelatedTo` fallback so no co-occurring pair is dropped.
- **Tier 2 — LLM layer adds (social/semantic):** `Ally`, `Enemy`, `Rival`, `Mentor`, `Student`, `Family` (+ `Parent`/`Child`/`Sibling`/`Spouse`), `Romantic`, `Betrayed`, `Serves`, `Killed`, `Protects`, `Fears`, `Respects`.
- **Tier 3 — Identity family (schema day one, LLM-inferred, the showcase):** `SAME_AS`, `ALIAS`, `SECRET_IDENTITY`, `REINCARNATION`, `TRANSMIGRATED_INTO`. GLiNER never attempts these; the graph is fully functional without them.

### 5.4 The universal reveal mechanism (rule #1, concrete)
Every node, edge, and significant property carries:
- `first_seen_chapter` — when the fact first *exists in the text*.
- `revealed_chapter` — when the *reader* learns it (NULL/equal for ordinary facts; later for reveals).

The fence keys visibility on `revealed_chapter`. **Reveal timing is keyed to when the reader learns the fact, not the world.** (In LotM, the reader learns Zhou Mingrui = Klein in ch1 via transmigration even though no character ever does — so that identity edge reveals at ch1.) Property-level example: Klein's node exists from ch1, but `{rank: "Seer", revealed_chapter: 5}` stays hidden until ch5.

---

## 6. Architecture

```
INGESTION  →  EXTRACTION  →  STORES  →  FENCE QUERY LAYER  →  API  →  FRONTEND
 clean/split   GLiNER (floor)   SQLite (truth)   the one chokepoint   FastAPI   React +
 chunk         + LLM (enhance)  vector store     revealed_chapter<=N            Cytoscape
```

- **SQLite is the source of truth.** The graph projection and vector index are derived and fully rebuildable from SQLite + raw chapters.
- **All SQL lives in `db/repository.py`.** One audit point.
- **All spoiler filtering passes through `query/fence.py`.** One enforcement chokepoint, applied at the SQL/index level (never post-filtered), keying on `revealed_chapter`.
- **Provenance everywhere:** each entity/edge records its extraction method (`gliner` | `rule` | `llm`) and an evidence span (a short quote) so any element traces back to its source text.

Target package layout: `storyweave/{config,db,ingest,nlp,graph,search,query,api,cli}`, plus `frontend/`, `eval/`, `tests/`, `data/{raw,samples,labels}`, `docker/`.

---

## 7. Build plan — phases 0 → 9

One phase at a time. End green → commit → **push to GitHub** → review → next. Each phase yields an interview-defense note + acceptance checklist.

### Phase 0 — Scaffold, schema, git, backup
- Two-venv setup (3.14 light, 3.12 ML); directory tree; pyproject + split requirements (light vs ML); ruff + mypy(strict) + pytest config; FastAPI app with `/health`; `storyweave` CLI skeleton.
- **The full 8-type schema from day one** (§5): nodes, subtypes, 3-tier relationship vocab, and universal `first_seen_chapter` + `revealed_chapter` on nodes, edges, and a node-property mechanism. All SQL in `db/repository.py`.
- **git init + first commit + create private GitHub repo + push.** Backup is part of Phase 0, not deferred.
- **Acceptance:** `pytest`/`ruff`/`mypy` green; `/health` serves; schema present; repo pushed to GitHub.

### Phase 1 — Ingestion & data model
- Cleaner (NFKC, de-hyphenate, config-driven cruft stripping, paragraph-preserving); chapter splitter; sentence-aligned chunking with exact `char_start/end` offsets; idempotent `storyweave ingest` (hash-matched, no dupes); per-work `storyweave.toml` config loader (novel-specific knobs are data, never code).
- Ship a small CC0 sample novel for tests/demo/CI.
- **Acceptance:** double-ingest yields no dupes; `clean_text[start:end] == chunk.text` for every chunk; ingest/db tests green; pushed.

### Phase 2 — GLiNER entity extraction (the floor)
- **First action: environment gate** — stand up `.venv-ml` (Python 3.12), install GLiNER + torch, prove a real smoke extraction works (GPU or CPU). Pin versions. Only then build.
- GLiNER over each chapter's clean text, prompted with the 8 type labels (+ subtype hints). Persist raw candidate mentions (surface, type, subtype, char span, ordinal) before clustering.
- Alias/coreference clustering into canonical entities, each with `first_seen_chapter`.
- `eval/ner_eval.py` with hand-labeled chapter(s) including Concept-type entities; per-type P/R/F1.
- **Acceptance:** places typed as places, Concept entities found, OOV/junk handled; eval prints real numbers; pushed.

### Phase 3 — Tier-1 relationships + graph projection
- Structural relationship extraction (Tier-1 list) via proximity + rule/dependency cues over clean entities; `RelatedTo` fallback; method + evidence-span + reveal stamps on every edge.
- `graph/builder.py` (SQLite → NetworkX, fenced by N) + `graph/serialize.py` (→ Cytoscape JSON carrying type, subtype, reveal stamps). Edge included only if both endpoints are visible at N.
- **Acceptance:** connected, correctly-typed, fenced graph with zero LLM (the graceful-degradation floor, proven); valid Cytoscape JSON; pushed.

### Phase 4 — Vector store + RAG search
- Embed chunks (sentence-transformers, batchable, `--device`), store each vector WITH its reveal stamp + `work_id`; one adapter interface, Chroma (dev) + FAISS (scale); RAG retrieves fenced top-k → cited answer (extractive offline default + opt-in LLM compose).
- **Acceptance:** fenced cited search end to end; late chapter unreachable at low N; both backends pass identical tests; pushed.

### Phase 5 — The spoiler-fence query layer (keystone)
- Consolidate all fencing into `query/fence.py` — one chokepoint for graph + search, keying on `revealed_chapter`, both-endpoints rule, identity/reveal handling. SQL stays in repository, vector filter stays in store; fence is the sole sanctioned caller.
- Permanent `test_fence.py` P0 regression: late node/edge/property hidden at low N, visible at high N, including an identity reveal.
- **Acceptance:** provably no unfenced path; P0 test green; pushed.

### Phase 6 — API
- FastAPI routes: `/ingest`, `/works`, `/graph` (n mandatory), `/entity/{id}`, `/search` (n mandatory), `/health`, delete-work. No unfenced path reachable from the client.
- **Acceptance:** endpoints fenced and working; missing/negative n → 422; pushed.

### Phase 7 — LLM enhancement layer (optional; the VRAM-gated stage)
- **First action: LLM go/no-go test** — small quantized model on GPU, else CPU+RAM, else Colab; document the chosen path. Off by default behind a config flag.
- Tier-2 social relationships, context disambiguation (Hermes-language vs deity), junk rejection, and Tier-3 identity inference (the Zhou Mingrui ⇄ Klein showcase, fenced on `revealed_chapter`).
- **Acceptance:** with LLM on, Tier-2 + identity edges appear; with it OFF, clean fallback to the Phase 3/5 floor (graceful degradation IS the test); pushed.

### Phase 8 — Frontend (the demo)
- React + Vite + TS; Cytoscape graph (8-type legend + subtypes, node size by importance, edge style by relation, evidence tooltips); the chapter slider driving the fence with bloom animation; Obsidian-grade navigation (zoom/pan/drag, zoom-dependent labels, type filters, node search); library/home screen with multi-novel switching + per-novel reading position; in-app ingest (browser upload → local pipeline via subprocess into .venv-ml → SSE progress → lands in library); delete controls; logo. Read the frontend-design skill first.
- **Acceptance:** slider blooms a clean correctly-typed graph; in-app ingest works end to end; multi-novel switching; UI not templated; pushed.

### Phase 9 — Packaging & hardening
- Dockerfiles + compose (api + frontend + volume), with an honest CPU-fallback path documented (GPU optional, not required to run); GitHub Actions CI (ruff + mypy + pytest on the light venv); README with hero GIF (recorded on the clean sample, not raw MTL), architecture diagram, honest caveats (extraction limits, two-venv rationale), and resume numbers filled in from real measured results.
- **Acceptance:** `docker compose up` runs the stack on a no-GPU machine; CI green on clean checkout; README complete; pushed.

---

## 8. Natural early-exit
Phases 0–5 alone (8-type ontology + GLiNER + structural graph + fenced search + the keystone fence) is a complete, shippable, fully-local product with no VRAM risk. Reassess appetite at the end of Phase 5 before committing to the LLM layer (Phase 7) and the full frontend/packaging push.

## 9. Risks (named up front)
- **GLiNER quality on heavily-translated MTL text** — likely good, not certain; Phase 2's eval measures it rather than assuming.
- **VRAM ceiling** — de-risked by CPU+16GB fallback; isolated to Phase 7 behind a go/no-go gate; Colab last resort.
- **Scope** — this is a full build; the Phase-5 early-exit is real. Commit to Phase 5, then choose.
- **Solo + no-recovery history** — mitigated by git-and-push from Phase 0, every phase.

## 10. Definition of done
`docker compose up` runs locally with no GPU required; loading a novel and dragging the slider blooms a clean, correctly-typed, fenced graph; search returns chapter-cited answers that never spoil ahead; the LotM identity reveal demo works with the LLM layer and degrades cleanly without it; CI green; README has the hero GIF, diagram, honest caveats, and real resume numbers; everything pushed to GitHub.
