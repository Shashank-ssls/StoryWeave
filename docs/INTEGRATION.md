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

### B1. "The Ninth House" — the bible and the text

Original CC0 fantasy court-intrigue serial, `docs/demo/the-ninth-house-bible.md` (the
ground truth) + `data/samples/the-ninth-house/` (40 chapters, ~11,300 words,
`LICENSE.md`, `storyweave.toml`). 89 named entities designed across all 8 ontology
types; 4 factions of 5+ Character members (House Ashcombe, House Vell, the Salt
Wardens, the Umbral Choir) to exercise org folding; 5 named arcs; 7 identity edges
across 6 distinct pairs (2 ALIAS, 2 SECRET_IDENTITY — one deepening into
REINCARNATION at ch34, the same pair, mirroring Hollow Crown's own ch2→ch4 Wren/
Caelum pattern — 1 standalone REINCARNATION, 1 TRANSMIGRATED_INTO), staggered ch5
through ch37 (early/mid/late). Two characters (Envoy Petra Hollis, Magistrate Wyle)
introduced only in the final arc with no earlier mention, for the not-yet-met search
tests.

**A real authoring gap, found and partly fixed, not hidden:** several bible-planned
Ability/Concept/Item terms were designed but never actually written into the 40
chapters' prose — a real mismatch between planning and execution, not a GLiNER
failure. Fixed for Abilities/Concepts (Quickhand, Voice of Command, Warden's
Discipline, Memory-warding, the Unmaking, Marrow-craft were each added into an
existing chapter with a small, natural insertion — MEASURED via `grep` before and
after) since these were plot-load-bearing. Left as a documented gap for Items: of
9 bible-designed items, only 3 (the Marrow Seal, Kaelen's Grimoire, the coded
ledger) and 1 Title (Scion of the Ninth House, never used) actually appear in the
final text. **The grading below is against entities that are actually IN the
text** (an extractor cannot be faulted for missing an input that was never
written), not the full aspirational 89-entity bible roster.

### B2. Arcs (D6) — backend implementation

`WorkConfig.arcs: list[ArcConfig]` (`[[arcs]]` in `storyweave.toml`) → persisted via
a new `arcs` table (`db/repository.py`) → served fenced (F6) through a new
`GET /works/{slug}/arcs?n=` route. F6 is enforced in SQL
(`list_arcs_fenced`'s `CASE WHEN start_chapter <= ? THEN name ELSE ''`), not
post-filtered: an arc's chapter RANGE is always sent (plain numbers aren't
spoiler-bearing), its NAME only once the reader's bookmark reaches
`start_chapter`. `ingest()` persists `cfg.arcs` when present (a no-op for Hollow
Crown, seeded directly via `seed.py`, never through `ingest()` — confirmed by the
unchanged full pytest count after this change).

MEASURED: `tests/test_fence.py` (2 new tests: name redaction + range-always-visible,
empty-arcs case), `tests/test_api.py` (2 new tests: the route over real HTTP, plus
a second arc-less work returning `[]`). Full suite after this change: 132 passed / 6
skipped (up from 124/6 — unchanged tests, +8 new), `ruff` clean, `mypy` clean (62
files after later additions).

### B3. The real GLiNER floor — measured extraction quality

**MEASURED**, `.venv-ml\Scripts\python.exe -m storyweave.cli.main ingest
data/samples/the-ninth-house --db <db>` then `extract the-ninth-house --config
data/samples/the-ninth-house/storyweave.toml --db <db>`, quoted verbatim:

```
work 'the-ninth-house' (id=1): +40 chapters, ~0 updated, =0 unchanged, +163 chunks, 0 cruft lines removed
work id=1: 887 mentions -> 226 entities (Ability:5, Character:62, Concept:21, Event:22, Item:29, Organization:16, Place:65, Title:6)
```

Then `relate the-ninth-house --config ... --db <db>`:

```
work id=1: 1584 Tier-1 edges (AffiliatedWith:8, HasAbility:19, HasTitle:31, LeaderOf:68, LocatedIn:444, MemberOf:60, OwnsItem:137, ParticipatedIn:133, RelatedTo:684)
```

**Methodology**: every one of the 226 extracted nodes was read by hand (dumped via
`repo.list_nodes`) and classified as a match to an in-text bible entity (any
reasonable surface-form variant — GLiNER/the clusterer frequently produced short
forms, e.g. `"Cassian"` not `"Cassian Ashcombe"`) or noise. This is a judgment call,
disclosed as such — not an automated fuzzy-match script — because the interesting
finding is qualitative (what KIND of thing gets over-generated) as much as the raw
number.

**Character — the strongest result: 100% recall.** All 31 in-text bible Characters
were found under some clustered surface form (first names, titles-as-name, etc.) —
zero missed. Precision was far weaker: 33 of 62 Character nodes are real matches
(53%); the other 29 are first/second-person pronouns (`I`, `he`, `she`, `you`, `my
lord`...) and generic common-noun stand-ins (`the trader`, `the masked guest`, `the
old woman`) that GLiNER's zero-shot "Character" label pulls in alongside real
proper nouns. Two real entities split across duplicate nodes (Vesper/Vey — its own
ALIAS pair, coincidentally; Petra Hollis/Envoy Hollis) rather than clustering to
one.

**Place — the weakest precision: ~22%.** Of 65 Place nodes, roughly 14 are real
matches to bible Places or Organizations GLiNER mistyped as Place (`House Ashcombe`,
`House Vell`, `the Ashen Court` — real entities, wrong ontology type). The remaining
~51 are generic common nouns describing a scene's furniture and geography (`desk`,
`door`, `table`, `hall`, `study`, `threshold`, `home`) — this is the single largest
source of noise in the whole extraction, a genre effect: a court-intrigue novel
narrates a lot of rooms.

**Type confusion is the dominant qualitative pattern, more than outright misses.**
Real entities frequently land under the WRONG ontology type rather than being
missed outright: `House Ashcombe`/`House Vell` (Organizations) → Place;
`Sallowmere` (a Place) → Character; `the Ashen Court`/`Chancery` (Places) →
Organization; `Memory-warding`/`Marrow-craft` (Abilities/Concepts) → Concept/missed
entirely; `Voice of Command` (an Ability) → Item; Title words (`Duchess`, `Maester`,
`Lord Regent`, `Envoy`) mostly get absorbed into the adjacent Character name
(`"Duchess Meraude Vell"` → node `"Meraude"`) rather than extracted as their own
Title node — only 3 of the roster's Titles (`Warden-Captain`→`"Captain"`,
`Choirmaster`, `Magistrate`) came out as clean, correctly-typed Title nodes.

**Clean recall misses** (real, in-text entities GLiNER never produced any node
for, under any type): `Vell Hall`, `the Unmaking`, `Thornmere Succession Law`,
`the Salt Tithe`, `the Choir Cipher` as a clean node (though `"ciphers"` was
extracted generically). The Marrow Seal, a named relic central to the plot,
was extracted only as generic `"seal"` — the specific proper name never survived
clustering.

**Rough aggregate precision ≈ 32%** (≈72 real-entity-matching nodes of 226 total,
counted generously across all cross-type matches) — noisy, exactly as CLAUDE.md's
own framing predicts ("GLiNER-only extraction is the FLOOR"), but the floor's
actual job — a complete, useful graph with zero LLM — holds: every named Character
in the book is findable, every faction is findable, the graph is dense (1584
Tier-1 edges, if noisy ones among them from the noisy nodes) rather than sparse.
The honest limitation is precision/type-fidelity on non-Character types in
dialogue-heavy prose, not coverage.

**Edge volume is a direct, measured consequence of node noise**: 1584 Tier-1
edges over 226 nodes (many generic) with a 320-char co-occurrence window
(`storyweave.toml`'s `relations.window_chars`, widened from Hollow Crown's 250
because this book's scenes run longer — see that file's own comment) produces a
denser-than-intended graph. Not fixed — the window is a per-work knob (data, not
code, per CLAUDE.md), and re-tuning it down would need its own sweep (Hollow
Crown's `relex_rel_threshold` was chosen this way, by a real sweep, per its own
`storyweave.toml` comment); out of this phase's scope, logged as a known limit.

### B4. The citation gate

**MEASURED**, `tests/test_ninth_house_citations.py`, reusing the project's own
`nlp.identity.citation_in_range` (not a reimplementation) against the real
committed chapter files:

```
9 passed in 0.32s
```

All 7 curated identity edges' `evidence_span` values occur verbatim
(whitespace/punctuation/case-normalized, the same tolerance the live citation gate
uses) in their claimed `revealed_chapter`'s text, AND do not occur in any earlier
chapter (a second test, `test_evidence_does_not_occur_in_an_earlier_chapter`,
checks the reveal is a genuine reveal — not already sitting in the text before its
claimed chapter).

### B5. Tier-2/Tier-3 curation

`storyweave/demo/seed_ninth_house.py` (`curate_ninth_house`) adds the layer an LLM
run would normally produce, provenance-tagged `ExtractionMethod.CURATED` — never
`llm` (I3; see the A1 decision log above for why this diverges from Hollow Crown's
own `llm`-labeled convention). Looks up real extracted node names (not invented
ones), so a missing/renamed node fails LOUDLY (`CurationReport.missing_nodes`),
never silently.

**MEASURED**, run against the real extracted+related DB:

```
work id=1: +7 identity edges, +12 social edges
```

Zero missing lookups — every curated edge's endpoints resolved against real
extracted nodes on the first attempt. Final graph: 226 nodes, 1603 edges (1584
Tier-1 + 7 identity + 12 social), 40 chapters, 5 arcs — all MEASURED via direct
repository queries against the built DB.

`tests/test_seed_ninth_house.py` (5 tests, light venv, no GLiNER needed) covers the
curation logic itself against a stub work: all 19 edges added, correct
tier/provenance, idempotent re-run (no duplication), loud failure on a missing
node, and the Sorrel/Aurelia Marrow pair specifically carrying both the ch20
SECRET_IDENTITY edge and its ch34 REINCARNATION deepening.

### B6. The extended seed command

`storyweave seed-demo` now takes `--ninth-house/--no-ninth-house` (default: both).
Hollow Crown seeds exactly as before (unchanged function, unchanged output) in
either venv. The-Ninth-House half needs `.venv-ml` — GLiNER imports lazily
(`nlp/extractor.py`), so running the full default under the light `.venv` seeds
Hollow Crown successfully, then fails with a clear, actionable message
(`"needs the GLiNER pipeline (.venv-ml)..."`) rather than a raw traceback.
MEASURED: both paths tested directly — light venv + `--no-ninth-house` (Hollow
Crown only, succeeds), light venv without the flag (Hollow Crown succeeds, then a
clean error), `.venv-ml` with no flag (full two-work reproducible build — see
timing in the performance section, Part C.3).

## Part C — End-to-end assimilation

*(filled in as Part C proceeds)*

## Known limits

*(filled in at close)*
