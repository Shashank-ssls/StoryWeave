# Retrofit progress — branch `retrofit/v2-core`

The v2 fixes applied inside v1. Rules: `docs/retrofit/CLAUDE_RETROFIT.md` (also pasted at
the top of `CLAUDE.md`). Phase prompts: `docs/retrofit/R0_*.md` … `R8_*.md`. Every number
below is labelled **[MEASURED]**, **[PREDICTED]** or **[PROJECTED]**.

Start of every session: read this file, state the current phase, do that one phase, stop.
No phase starts until the previous one is green, committed and pushed.

## Status

| phase | what | status | commit | key measured numbers | date |
| --- | --- | --- | --- | --- | --- |
| R0 | branch, rules, baseline rerun | **green** | `4ba8f80` | [MEASURED] frozen-DB SHA-256 match · ch40 206 nodes / 1316 edges served · fence 0 violations / 105,243 elements · relation micro-F1 0.0459 · entity F1 0.5319 · D1 = 1326 fenced rows → 1316 served (10 lost) · 1307 of 1326 edges are `rule` · 160 of 162 relation FPs are Tier-1 · env gate 10/10 in both venvs | 2026-09-28 |
| R1 | co-occurrence off + rescore on the v1 key | **green** | `8319c46` | [MEASURED] relation micro-F1 **0.0459 → 0.0000** (worse: all 5 v1 TPs were rule edges) · FP **162 → 2** (Tier-1 160 → 0) · FN 46 → 51 · ch40 edges served **1316 → 18** · isolated nodes at ch40 **0 → 186 of 206** · entity F1 unchanged at 0.5319 · D2 is now 100% of the projection loss (19 rows → 18 served) · fence 0 / 17,471 | 2026-09-28 |
| R2 | Stage 0 cleaner | **green** | `3b91545` | [MEASURED] 0 watermark hits / 0 homoglyphs over 44 committed chapters · clean text byte-identical to pre-R2 in **0 of 44 chapters changed** · residual Greek/Cyrillic **0** · injection round-trip **1,063 hits removed, 0 failures** · Shadow Slave **[NOT MEASURED]**, text absent from this machine | 2026-09-28 |
| R3 | 4 node types + `entity_labels` | **green** | `69a95e7` | [MEASURED] 4-type entity F1 **0.6076** strict / 0.6582 alias-aware on the PROJECTED key (different answer key — never a delta vs 0.532) · alias F1 **0.7500** (P=1.0000, R=0.6000), **over-merges 0**, under-merges 3→2 · fence **0 / 20,439** incl. 5,965 label elements, 2 label canaries fire · frozen DB serves, **0 / 95,530** · Hollow Crown digest identical · 806 mentions → 188 entities, 240 labels · title links **0 (correct: corpus has none)** | 2026-09-28 |
| R4 | 12 relations + validator + weight (fixes D1/D2) | **green (STOP CONDITION HIT)** | `f1204f0` | [MEASURED] STATED micro-F1 **0.0000** (TP=0 FP=3 FN=23) vs pre-registered 0.05–0.20 · STATED+INFERRED also 0.0000, so the both-names rule costs **0** recall · v1-key like-for-like 0.0000 (FP 2→3, FN 51) · 306 proposals → **64 edges, 37 STATED**, all ring 2, **0 ring-1 social edges** · rejections 137 ENDPOINT_NOT_STORED / 44 DOMAIN_RANGE / 0 all other codes · recall accounting 28 out-of-scope / 12 NO_PROPOSAL / 6 ENTITY_MISSING (all one entity) / 2 WRONG_TYPE / 1 VALIDATOR_REJECTED / 1 INFERRED / 1 FOUND · curated 12 of 19 would be accepted, 1 STATED · **D1/D2 fixed**: ch40 976 drawable rows → 976 payload edges, edge 1325 SECRET_IDENTITY preserved · fence 0 / 24,450 | 2026-09-29 |
| R4b | Organization recall (head-noun rule) | **green (partial: entities yes, relations no)** | `d31a43b` | [MEASURED] `ENTITY_MISSING` **6 → 0, stage eliminated** · but `NO_PROPOSAL` **12 → 18**, relation micro-F1 **0.0000 → 0.0000** · entity F1 4-type **0.6076 → 0.6250** (TP 24→25, **FP unchanged 17**) · Organization F1 **0.400 → 0.545** · over-merges **0 → 0** · 9 rule promotions → **3 new Organizations, 0 false positives, 0 lost** · 4 label-prompt candidates measured, **none recovered the class** · relation build bit-identical to R4 | 2026-09-29 |
| R4c | relex grounded on known entities | **green (negative result)** | `PENDING` | [MEASURED] ring-1 ch40 **4** (predicted 4–25) · ring-2 ch40 **64** (predicted 60–150) · STATED micro-F1 **0.0000** (predicted 0.05–0.25, **MISSED**) · `input_spans` accepted but **IGNORED** (byte-identical entity list, both NER modes) → snapping fallback · 30 spans snapped, `ENDPOINT_NOT_STORED` 137→115, edges 64→68, STATED 37→40 · recall accounting **unchanged in every stage** · **default view ch40 = 0 edges, 20/20 isolated** · 125 ungrounded endpoints are pronouns/common nouns (`She`×14), i.e. coreference not recall | 2026-09-29 |
| R5 | LLM recall pass (optional) | not started | — | — | — |
| R6 | salience per chapter + 4-clause query + ego API (fixes D3) | not started | — | — | — |
| R7 | frontend readability, timeline removed | not started | — | — | — |
| R8 | evaluation + projection check | not started | — | — | — |

Minimum viable demo path if time runs out: R0 → R1 → R4 → R6 → R7. R2, R3, R5 are
accuracy work; skipping them is a documented scope cut, not a failure.

---

## R0 — branch, rules, baseline snapshot · green, 2026-09-28

Full evidence: `evidence/retrofit/R0_baseline_rerun.md` and
`evidence/retrofit/R0_local_paths.md`. Logs: `evidence/retrofit/logs/R0_*.log`.

### Acceptance

- [x] Branch `retrofit/v2-core` exists, cut from `origin/integration/demo-scale`
      (`0202df1`), and is pushed.
- [x] `CLAUDE.md` starts with the retrofit block; the old five non-negotiable rules are
      marked superseded where they conflict (rules 2 and 3), not deleted.
- [x] `python tools/check_local_env.py` passes in both venvs — 10/10 checks, tables
      pasted in `R0_local_paths.md` §1–2.
- [x] Frozen DB hash matches `evidence/BASELINE.md`
      (`c7264c16…d946ff`, 847,872 bytes, still read-only).
- [x] Baseline rerun reproduces all four v1 figures, no unexplained mismatch:
      206 nodes / 1316 edges served at ch40 · 0 fence violations over 105,243 elements ·
      relation micro-F1 0.0459 · entity F1 0.5319.
- [x] pytest / ruff / mypy: pre-existing tests unchanged (`152 passed, 6 skipped` with the
      new file aside; `167 passed, 6 skipped` with it), mypy unchanged
      (`no issues found in 78 source files`), **ruff improved from `Found 20 errors.` to
      `All checks passed!`** — see the honesty note below.
- [x] `R0_local_paths.md` written with the C: size baseline.
- [x] Commit `chore(retrofit): R0 branch, rules, baseline rerun` + push.

### Numbers established for later phases to beat — all [MEASURED]

| quantity | R0 value |
| --- | ---: |
| edge rows in the DB (`work_id = 2`) | 1326 |
| rows passing the fence at ch40 | 1326 |
| edges served by `/graph?n=40` | 1316 |
| edges from the co-occurrence rule | 1307 (98.6%) |
| of those, `RelatedTo` never-drop fallback | 565 |
| nodes served at ch40 | 206 |
| relation FPs that are Tier-1 | 160 of 162 |
| alias over-merges / SAME_AS false positives | 0 / 0 |
| fence violations | 0 over 105,243 elements |

### D1 and D2 confirmed, not fixed (R4 fixes them)

`nx.DiGraph` cannot hold parallel edges, so 10 of the 1326 fenced rows are overwritten in
the projection layer. Nine are `RelatedTo` co-occurrence edges (which R1 deletes anyway);
the tenth is the real defect, **D2**: on pair 14 → 150 the curated `SECRET_IDENTITY` edge
(id 1325) is overwritten by `REINCARNATION` (id 1327). Every collision is a curated
Tier-2/3 edge landing on a pair the rule builder had already claimed, so a multigraph (or
a per-pair relation list) fixes both at once. Full table of all ten in
`R0_baseline_rerun.md` §3.

### Two things R0 fixed that it had to

1. **`tools/eval_fence.py` could not run against the frozen DB.** `_copy_db` used
   `shutil.copy2`, which preserves mode bits, so the throwaway copy of the read-only
   baseline was itself read-only and the negative control died with
   `sqlite3.OperationalError: attempt to write a readonly database`. The copy is now
   chmod'd writable; the source is still never opened for writing.
2. **`ruff check .` was red at the baseline (20 errors), so CI was red.** All 20 were
   cosmetic and all in `tools/`: 17 over-long lines, 2 unsorted import blocks, 1
   placeholder-less f-string. Fixed by wrapping and sorting. One non-mechanical edit: a
   long ternary in `run_evidence.py` became a named `counts_agree` variable with identical
   truthiness. No behaviour change, and §2.1 of the rerun re-derives the same metrics.
   `storyweave/` and `frontend/` were not touched, per R0's "do not".

### Honesty note

R0's acceptance asks for the gates to be "unchanged from baseline". Two of the three are
exactly unchanged. Ruff is **better** than baseline, not unchanged, and that is stated
rather than glossed: the baseline was 20 errors, which means the claim "the original build
ended green on ruff" was not true of this commit for `tools/`. The 20 findings are listed
above so the change is auditable.

### Viva defense

R0 buys the one thing the retrofit cannot fake: a like-for-like starting point measured in
this checkout, so every later delta is a real delta and not a comparison against numbers
copied out of a previous session's report. It also converts the "nothing on C:" rule from
a habit into an executable gate with 15 tests behind it — the variable that was actually
leaking was `TEMP`, which no cache setting would have caught. The rerun confirms the
retrofit's premise at the source rather than on trust: 1307 of 1326 edges come from the
co-occurrence rule, and 160 of 162 relation false positives are Tier-1, so R1 — switching
one flag off — is aimed at the whole of the measured error, not a slice of it.

---

## R1 — co-occurrence off + rescore · green, 2026-09-28

Full evidence: `evidence/retrofit/R1_RESULT.md`. Logs: `evidence/retrofit/logs/R1_*.log`.

### Acceptance

- [x] Unit test: config flag off → zero rule edges created
      (`test_cooccurrence_disabled_by_default_creates_no_edges`).
- [x] Unit test: rule rebuild does not delete other producers' edges
      (`test_rule_rebuild_does_not_delete_other_producers_edges`) — covers rule ON, a
      re-run, and rule OFF, against `gliner`/`llm`/`curated` edges on the same pair.
- [x] `R1_RESULT.md` written with the v1 vs rule-off table, **both** scopes
      (`chapter_local` and `cumulative`), per relation with counts, per tier, and density.
- [x] Green gates: `ruff check .` clean · `mypy` `no issues found in 78 source files` ·
      `pytest` `169 passed, 6 skipped` (167 + 2 new).
- [x] Commit `feat(retrofit): R1 co-occurrence off by default + rescore`, pushed.

### The measured micro-F1, stated plainly

**Relation micro-F1 pooled `chapter_local`: 0.0459 → 0.0000.** `cumulative`:
0.0623 → 0.0000. **The number got worse.** All five of v1's true positives (4 `LocatedIn`,
1 `RelatedTo`) were themselves co-occurrence edges, so deleting the rule deleted them:
TP 5 → 0, FP 162 → 2, FN 46 → 51. The retrofit's projection that removing co-occurrence
raises relation F1 is **not supported** by this measurement.

What it did buy: **160 of 162 false positives removed** (Tier-1 FP 160 → 0; the 2 that
remain are hand-curated, one `Respects` and one `TRANSMIGRATED_INTO`), and an honest
statement of the hole — **51 missing relations and 186 of 206 nodes isolated at ch40**,
median degree 0. That is R4's and R5's work order, now sized. Nothing in the rule-off
graph is shippable as a reader experience; R7 must not be run against it.

Controls held: entity F1 (0.5319 strict / 0.5745 alias-aware), alias clustering
(P=1.0000, 0 over-merges), entities per chapter and nodes served are all **identical** to
v1, which is what makes this like-for-like.

### Two findings for later phases

1. **D2 is now the entire projection loss.** 19 curated rows at ch40 serve as 18, and the
   one lost row is `SECRET_IDENTITY` (edge 1325, pair 14 → 150, overwritten by
   `REINCARNATION`). In R0 it hid among nine junk collapses; now it is 100% of the loss and
   the element it destroys is an identity reveal. R4's multigraph fix is load-bearing.
2. **Do not build R6's salience on degree.** The scorer's ranking metric fell (P@10
   0.4000 → 0.3000, MAP 0.4414 → 0.3668) purely because it ranks by fenced payload degree
   (`tools/eval_score.py:293`). After R1 there is almost no degree left to rank on, so R6
   must rank on mentions up to chapter *n* (plus cited-edge degree once R4 supplies edges).

### One latent bug fixed

`repo.clear_edges(work_id)` deleted **every edge of every tier** on each Tier-1 rebuild, so
re-running `relate` on the seeded Ninth House would have silently wiped its 19 hand-curated
Tier-2/Tier-3 edges. The builder now uses a new `clear_edges_by_method` (all SQL still in
`db/repository.py`) scoped to `extraction_method='rule'`, and a test pins it.

### Viva defense

R1 is the phase that proves the project measures rather than asserts: it was run expecting
the F1 to rise, it fell to zero, and the report says so in its first line. The finding is
sharper than the projection was — v1's relation score was not merely noisy, it was
*entirely* an artifact of the co-occurrence rule, including all five of its correct
answers, so there was no real relation extraction in v1 to improve on. Removing 160 of 162
false positives while losing 5 true positives is the right trade only because R4 follows:
precision is now recoverable by construction (every edge cited), whereas under
co-occurrence it was capped at 0.030 no matter what was added on top.

---

## R2 — Stage-0 cleaner · green, 2026-09-28

Full evidence: `evidence/retrofit/R2_cleaner_audit.md`. Log:
`evidence/retrofit/logs/R2_cleaner_audit.log`.

### Ordering note (decision recorded, then superseded)

R2 was first **deferred** on the grounds that the measured corpus (The Ninth House) is
clean text and R2 affects only Shadow Slave, with the constraint that it must run before
any Shadow Slave re-extraction and **never between R3 and R4**. It was then run
immediately instead. No R3 work had begun — the R3 session had only read source files, made
no edits — so R2 sits cleanly **after R1 and before R3**, which satisfies the constraint
rather than violating it. The deferral rationale turned out to be correct and is now
measured rather than assumed (see below), so nothing was lost by running it early, and R3
gains a guarantee it would otherwise have lacked: its re-extraction cannot be confounded by
cleaner changes.

### Acceptance

- [x] All tests pass; watermark hit counts logged to `R2_cleaner_audit.md`.
      **Ninth House 40 chapters: 0 hits. Hollow Crown 4 chapters: 0 hits.
      Shadow Slave: [NOT MEASURED]** — its text is gitignored and absent from this
      machine (`data/raw/` holds only `.gitkeep`), so the count is not estimated. Re-run
      `tools/cleaner_audit.py --corpus data/samples/shadow-slave` once the text is
      restored; **R2 must be re-audited before Shadow Slave is re-extracted.**
- [x] Unicode audit: **zero Greek/Cyrillic code points** left in clean text, all corpora.
- [x] Green gates: `ruff` clean · `mypy` `no issues found in 81 source files` ·
      `pytest` `185 passed, 6 skipped` (169 → 185, 16 new cleaner tests).
- [x] Commit `feat(retrofit): R2 stage-0 cleaner`, pushed.

### The measured result

**R2 changes nothing on the measured corpus, and that is proved rather than assumed.** The
audit cleans every chapter twice — once with all four R2 steps on, once with them off — and
compares: **0 of 44 chapters differ.** The only non-ASCII character in the Ninth House
source is U+2014 EM DASH (117 occurrences). So:

- R3's re-extraction is **not** confounded by R2: clean text is unchanged, therefore
  character offsets are unchanged, therefore post-R2 entity offsets remain directly
  comparable to the frozen v1 baseline.
- Hollow Crown cleans identically (rule I2 holds).

Because a no-op audit cannot show the cleaner *works*, and the corpus that would show it is
absent, `--inject-check` splices the four real watermark forms into every paragraph of all
44 committed chapters and requires byte-identical round-trip: **1,063 watermark hits
removed, 0 failures.** Pinned by a test, so a future regression fails the suite instead of
the audit printing a cheerful `OK`.

### Decisions

- **Watermark tags strip markup, keep inner text.** These wrappers enclose real story
  prose — deleting the block would delete part of the chapter. Tag names are per-work data
  (`cleaner.watermark_tags`).
- **Quote kind is preserved and brackets are never touched.** `'` is never promoted to `"`
  (it is also the apostrophe in `don't`, and singles mark thought vs. doubles for speech);
  `[Can you hear me?]` keeps its brackets because they are content.
- **Folding is confusables-only.** 54 table entries, each annotated with code point and
  Unicode name. Greek/Cyrillic letters with no Latin twin (`π`, `λ`, `ς`) are left alone and
  *reported*, so a genuine Greek quotation surfaces as a decision, never as silent
  corruption.
- **Order is load-bearing and tested both ways:** with folding off, the same real watermark
  yields 0 hits. The failure mode is demonstrated, not described.

### Verified, not rebuilt

Offsets already indexed into clean text in v1; confirmed against the frozen DB read-only:
**163/163 chunks and 887/887 mentions** satisfy `clean_text[start:end] == text/surface`, 0
violations. Raw source files are read and never written.

### Viva defense

R2's honest result is that it removes nothing from the corpus being measured — so the phase
is justified by what it *prevents* rather than what it fixes, and the report leads with
that instead of hiding a row of zeros. The engineering content is the ordering argument:
these watermarks are obfuscated with Greek homoglyphs specifically so that a
regex-first cleaner misses them, which is why folding precedes pattern matching, and the
test suite proves the wrong order fails. The 1,063-hit injection round-trip is what lets me
claim the cleaner works without the corpus that motivated it, and the zero-diff audit is
what lets R3 attribute its entity delta to the ontology change alone.

---

## R3 — four types + entity_labels · green, 2026-09-28

Full evidence: `evidence/retrofit/R3_RESULT.md` (read §0 first — the scoring key changed).

### Acceptance

- [x] `check_local_env.py --c-drive-report` passes; C: sizes match the R0 baseline
      (`.cache` 135.8 MB unchanged; pip/Ollama/Playwright still absent). Nothing downloaded.
- [x] Migration up/down on a fixture DB (`test_migration_up_then_down`); up on a copy of the
      frozen baseline wrote 293 labels / 219 entities, idempotent, down clean.
- [x] Label-reveal fence tests pass, plus the harness surface: **0 violations over 20,439
      elements (5,965 of them labels)**, two negative controls both firing.
- [x] Entity P/R/F1 per type with counts, and alias P/R/F1 with over/under-merge counts,
      in `R3_RESULT.md`.
- [x] **Over-merges = 0.**
- [x] Gates: ruff clean · mypy 85 files · pytest **221 passed, 6 skipped** (185 → 221).
- [x] Commit + push.

### The mapping (per the user's decision, which overrode R3 task 1)

Stored `NodeType` unchanged (8 values, same CHECK, same validation); new `GraphNodeType`
(4) is all that new extraction may write and the payload may serve; `LEGACY_TYPE_MAP`
documents each old type's fate. Enforced in three independent places: labels prompt 4 types
(nothing created), `add_node` rejects (nothing stored), and the payload query adds
`type IN (...)` **after** the fence clause (nothing legacy served). No migration.

### Two bugs the display filter exposed

1. `nx.add_edge` silently created attribute-less **phantom nodes** for undrawn endpoints,
   failing payload validation. Edges with undrawn endpoints are now skipped.
2. A **pre-R3 database crashed the new label reads** (`no such table: entity_labels`) — the
   frozen baseline is read-only and cannot be migrated on the fly. `has_entity_labels_table()`
   probes once; such a database serves with `nodes.name` as the fallback label.

### One I2 deviation, stated not buried

`test_all_eight_node_types_present_by_final_chapter` asserted the Hollow Crown **payload**
carries all 8 types — the exact thing R3 reverses. It is now
`test_all_eight_node_types_stored_but_only_four_are_drawn`, asserting both halves (still
stored, still fenced, only 4 drawn), which is strictly stronger. **No seeded data changed**:
the fixture digest `e73a69c0…c482` was recorded before any R3 code and is asserted in a test.

### Aliases — the R4-critical number

P=1.0000 R=0.6000 **F1=0.7500**, **0 over-merges**, under-merges 3 → 2 (v1's
`'scribe'+'sorrel'` miss fixed). Both remaining are `'captain'` ↔ `Orin Drask`, refused by
two rules independently: `captain` is inside the hyphenated `Warden-Captain` so it is not a
contiguous token subsequence, and it is a bare role word. All 19 whole-corpus refusals are
listed with reasons in `R3_RESULT.md` §5.

Two fixes the measurement forced: the 6-chapter window refused **16 correct** shortenings
(`juno`→`juno stray` etc.), so it is 40 for this work in `storyweave.toml` (swept: 6/10/20/40
→ 27/29/38/41 merges, over-merges 0 throughout); and widening it admitted
`'girl'→'chancery girl'`, so bare person/role nouns joined the generic set.

### Title linking: 0 links, correctly

The corpus has **no** comma-bracketed title apposition — verified by grepping all 40
chapters independently of the code (zero matches both directions). The first implementation
produced two links and **both were wrong** (a possessive, "the Ninth House's"; and a fronted
prepositional phrase, "At the Chancery, Ser Robart Kell"). Four guards later: 0 accepted, 0
wrong. Reported as a negative result.

### Viva defense

R3's substance is that it narrowed what the graph draws without migrating a single row: two
vocabularies and one documented mapping, enforced at creation, storage and serving, so the
frozen v1 database and the Hollow Crown fixture still load and serve untouched. The phase
also shows the measurement earning its keep three times — the chapter window was refusing 16
real aliases, widening it exposed a latent over-merge, and the title linker's only two
outputs were both false positives. Each was found by running the thing on real text rather
than by reasoning about it, and the 4-type entity score is reported on its own key because a
delta against 0.532 would be arithmetic on two different answer keys.

### Next phase

R4 (closed relations + validator). **No download needed**: relex is present and loads with
`HF_HUB_OFFLINE=1`. **R4 is fully Ollama-free** — its edges come from GLiNER-RelEx plus the
rule validator; the LLM tier is R5's and R5 is optional.

---

## R4 — PRE-REGISTRATION (written before the first scoring run, never edited)

**Expected STATED-only relation micro-F1 on the 12-relation projection of the
annotation: [PREDICTED] 0.05 – 0.20.**

Reasoning (one line, as required): GLiNER-RelEx is zero-shot on unseen fantasy prose and
the STATED grade additionally demands both participants' labels *and* a relation cue inside
a single verbatim quote, which this book's pronoun-heavy narration will frequently fail —
so recall should be low and precision high, on a key that has dropped the structural
relations v1 never got right.

Set before scoring and without reading the annotation's gold relations or quotes: the
per-relation cue lists, the relex confidence threshold (the already-configured default),
and the kin guard. Any threshold sweep is a diagnostic table only and does not select the
shipped value. The 19 hand-curated seed edges are not extraction output and are excluded
from every score.

---

## R4 — twelve closed relations + validator + weight · green, 2026-09-29

Full evidence: `evidence/retrofit/R4_RESULT.md`. Logs: `evidence/retrofit/logs/R4_*.log`.

**The pre-registered band was 0.05–0.20. The measured STATED micro-F1 is 0.0000, below
the phase's 0.05 stop condition. The validator was NOT loosened.** R4 reports and stops
so the next step can be decided together.

### Acceptance

- [x] `check_local_env.py --c-drive-report` passes 10/10; C: `.cache` 135.8 MB, unchanged
      from the R0 baseline; pip / Ollama / Playwright still absent. Nothing downloaded.
- [x] Unit tests for every validator branch on real corpus strings, including both cases
      the brief names: `"...such a wonderful little sister?"` **rejected** (`KIN_GUARD`),
      `"The Saint looked at his niece"` **accepted**.
- [x] D1/D2 regression tests pass. Edge 1325 `SECRET_IDENTITY` and edge 1327
      `REINCARNATION` both reach the payload with their own relation strings; payload
      edge count == fenced drawable row count, and the id SETS are equal, at chapters
      1, 5, 9, 17, 25, 37, 40.
- [x] Rejection counts by reason and relation counts per type in `R4_RESULT.md`,
      all [MEASURED]. SAME_AS reported as counts (0 extracted, 5 curated), not F1.
- [x] Gates: ruff `All checks passed!` · mypy `Success: no issues found in 66 source
      files` · pytest **253 passed, 6 skipped** (221 → 253).
- [x] Pre-registration committed BEFORE the first scoring run (`d99e445`) and not edited.
- [x] Curated seeds excluded from every score and reported separately.
- [x] Commit + push.

### The result, stated plainly

R4 built a relation extractor where R1 left none: 306 proposals, **64 edges, 37 STATED**,
every one carrying a verbatim quote. **None of them is one of the 23 relations the key
asks for in the scored chapters**, and **all 64 are ring 2** — the seven ring-1 social
relations got zero edges, so R4 produced an overlay and not a graph.

The recall accounting says where the 51 gold relations went, and it is the phase's real
output: **28 (54.9%) are outside the closed twelve by design** and will never be
produced; **12 (23.5%) are pure model-recall misses** where both entities exist and relex
proposed nothing — that is R5's target; **6 (11.8%) are all downstream of ONE missing
Organization** (`Salt Quarter watch`), so entity recall is the cheapest relation win
available; and exactly **1 reached the validator and was refused**. The validator is
provably not the bottleneck.

### Three findings for later phases

1. **Do not spend R5 on the gate.** One gold relation in 51 was lost to the validator.
   Loosening it cannot raise the score; supplying proposals can.
2. **Entity recall and relation recall are not independent.** One missing Organization
   cost six relations, and one mistyped entity (`House Vell` typed Place, not
   Organization) cost the only `DOMAIN_RANGE` refusal of a gold relation.
3. **A curated citation does not check out.** `Thessaly -Mentor-> Mira` has an
   `evidence_span` that is not verbatim in chapter 7 of the clean text. That is a finding
   about the seeded data, not the validator.

### Two deviations, stated not buried

1. The Hollow Crown digest test now spells out its column list instead of `SELECT *`,
   because R4's seven additive `edges` columns would otherwise change the digest with no
   seeded value changing. **The expected hash is unchanged** (`e73a69c0…c482`), so the
   I2 guarantee is intact rather than re-baselined.
2. The unique index on `(work_id, relation, source_id, target_id)` is **partial**
   (`WHERE grade IS NOT NULL`), scoped to rows R4's validator wrote. A full index broke
   the Phase-7d coref merge, which legitimately keeps two same-relation edges on one pair
   at different tiers.

### Viva defense

R4's honest result is that it built a working relation extractor and scored zero, and the
report leads with that rather than with the 37 cited edges it could have led with. The
phase is defensible because it was pre-registered: the band was committed before the
first run, the cue lists and thresholds were fixed without reading the answer key, the
curated seeds were held out of the score, and when the number came in under the stop
condition nothing was loosened to rescue it. What it delivers is a diagnosis instead of a
number — four separately actionable loss stages — plus a genuine fix to D1/D2, where the
`SECRET_IDENTITY` reveal v1 silently overwrote now reaches the payload, pinned by a
set-equality test at seven chapters.

### Next phase

R5 (LLM recall pass) is now clearly aimed: 12 of 51 gold relations are `NO_PROPOSAL` on
pairs whose entities already exist. It remains optional, and the alternative — fixing the
entity miss that costs six relations — may be cheaper. **Decide before starting.**

---

## R4b — Organization recall · green (partial), 2026-09-29

Full evidence: `evidence/retrofit/R4b_RESULT.md`. Logs: `evidence/retrofit/logs/R4b_*.log`.

**Scoped to fix the CLASS behind R4's `ENTITY_MISSING`, not the instance.** The gold
annotation was never opened during diagnosis, the prompt probe or the rule design, and no
gold entity is named anywhere in the rule, its vocabulary or the config.

### The result, stated plainly

**The general fix works at the entity layer and recovers ZERO of the six relations.**
`ENTITY_MISSING` goes 6 → 0 — the stage is eliminated — but those six relations move into
`NO_PROPOSAL` (12 → 18) rather than becoming true positives, and relation micro-F1 is
0.0000 before and after. The rule was **not** narrowed to make the number move.

**Why**: GLiNER-RelEx runs its OWN NER internally and is never given the graph's entity
list, so it reproduces the identical nested-span error one stage later — it sees
`Salt Quarter` (a Place) and never proposes a relation whose endpoint is
`Salt Quarter watch`. Fixing the entity layer cannot reach the relation layer while the
two stages independently repeat the same step. That is the phase's real finding.

### Diagnosis, from the text only

The whole class is **5 phrases in 40 chapters**, each occurring once. Three already
became Organizations; two produced **no mention at all**, so the fault is upstream of
clustering, significance and the four-type write check — all three are excluded by
measurement, not argument.

**The label prompt is not the fix, and that was measured before any rule was written**:
four candidate prompt additions ("group of people", "military unit", "institution", all
three) were run over every relevant sentence and **none recovered the class**; the
nested-Place reading survived every one.

### What the rule created — all 40 chapters

9 rule-derived mentions → **3 new Organization nodes, 0 false positives, 0 lost**:
`Salt Quarter watch`, `Cassian's guard`, `Vell family`. The other 6 promotions reinforced
organizations the model had already found. Entity F1 0.6076 → 0.6250 with **false
positives unchanged at 17**, Organization F1 0.400 → 0.545, **over-merges 0**.

Two false-positive iterations are recorded in the report with their general fixes
(`'A ring'` → exclude sentence-initial determiners; `'And House'`/`'If House'` → exclude
the whole closed class of English function words, because a proper modifier is an
OPEN-class word). Neither fix blacklists the word that broke.

### Gates

ruff `All checks passed!` · mypy `Success: no issues found in 69 source files` ·
pytest **266 passed, 6 skipped** (253 → 266, 13 new).

### Viva defense

R4b refused the cheap win. The brief's risk was a rule shaped around one gold entity, so
the diagnosis ran with the annotation closed and the design was decided by a NEGATIVE
measurement — four prompt additions, none of which recovered the class. The shipped rule
is a general English construction whose two false positives were fixed by widening a
guard to a closed word class rather than blacklisting the offenders. The outcome is
honest in both directions: the entity layer genuinely improved and the relation score did
not move one thousandth, and the reason why is a specific, testable defect in how relex
is wired.

### Next

Before R5: relex is handed raw text and re-discovers entities it should be told about.
Feeding the graph's known spans into relation extraction is the change that converts these
six, and it is likely cheaper than the LLM pass. **Decide between the two before starting.**

---

## R4c — PRE-REGISTRATION (written before the R4c run, never edited)

**Correction to R4 and R4b first.** Both reports said every R4 edge was ring 2 ("all 64
are ring 2", "R4 produced an overlay and no graph"). That is **wrong**, and the error was
found by building `tools/r4c_report.py` and counting rings directly: **SERVES is a ring-1
relation** (retrofit rule 3 lists it there), so R4/R4b have **4 ring-1 edges at ch40**, of
which **1 is STATED**. The corrected baseline is below. The substantive claim those
reports made — that no *social* graph reached the reader — survives, because the default
view still has zero edges; but the number was stated wrongly and is corrected here rather
than quietly fixed.

### Measured R4b baseline (existing data, not the R4c experiment)

| chapter | nodes | edges | ring1 | ring2 | STATED |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 86 | 22 | 3 | 19 | 11 |
| 20 | 134 | 28 | 3 | 25 | 14 |
| 30 | 153 | 45 | 3 | 42 | 25 |
| 40 | 191 | 64 | **4** | 60 | 37 |

**Default view at ch40 (Characters only, cast=20, STATED): 0 edges, 20 of 20 isolated.**

### Predictions for R4c — [PREDICTED]

| quantity | predicted band |
| --- | --- |
| ring-1 edges at ch40 (fenced, drawn, any grade) | **4 – 25** |
| ring-2 edges at ch40 (fenced, drawn, any grade) | **60 – 150** |
| STATED micro-F1, 12-relation key | **0.05 – 0.25** |

Reasoning, one line: constraining relex to the stored mentions removes the nested-span
failure that made endpoints unground-able, so the 12 `NO_PROPOSAL` gold relations become
reachable and ring-2 should grow the most (it is what the corpus states plainly); ring-1
should move least, because the book's kinship and alliance claims are mostly pronominal
and the STATED rule still demands both names in one quote.

Unchanged from R4's own pre-registration and not re-tuned: the model, the fixed relex
thresholds (ner 0.3 / rel 0.6), the cue lists, the kin guard, the validator.

---

## R4c — relex grounded on known entities · green (negative result), 2026-09-29

Full evidence: `evidence/retrofit/R4c_RESULT.md`. Screenshots: `evidence/retrofit/shots/R4c/`.

**Pre-registered (`5d25d3a`) and missed on the headline.** ring-1 at ch40 landed at 4
(band 4–25) and ring-2 at 64 (band 60–150), both at the floor of their bands; **STATED
micro-F1 came in at 0.0000 against a predicted 0.05–0.25**.

### Which path, and why

The brief's primary path — hand relex the stored spans — is **unavailable**:
`GLiNER.inference` has `input_spans`, **accepts it, and ignores it**. Measured: the
returned entity list is byte-identical with and without it under `flat_ner` both True and
False. So R4c used the snapping fallback (overlap-match each returned span to the stored
mention in the same chapter, shortest wins on ties), with the candidate list built through
`fence.visible_nodes` so a later reveal can never be a snapping target earlier.

### What it bought, and what it did not

30 spans rescued · `ENDPOINT_NOT_STORED` 137 → 115 · edges 64 → 68 · STATED 37 → 40.
**Recall accounting did not move in a single stage**, all three scores stayed 0.0000, and
the default view at ch40 is still **0 edges with 20 of 20 cast isolated**.

The residue localises the remaining loss: of 125 endpoints that still ground to nothing,
the largest group is **pronouns** (`She` ×14, `she` ×6, `He`, `I`) and the next is common
nouns (`secret`, `birds`, `realm`). Those are **coreference and junk, not missed
entities** — snapping has no target to snap to, and the junk should be refused.

### Two of my earlier claims corrected by evidence

1. R4b said relex "never proposes the full span" for `Salt Quarter watch`. **Wrong** — free
   NER does return it. The loss was relations proposed between `him` / `watch` / `Drask`,
   which no stored surface matched. Right stage, wrong mechanism.
2. I said this session that the frontend has no cast-size or type controls. **It has
   both** (`show-people`, `show-orders`, `show-places`, `cast-principal`/`cast-everyone`).
   Running the app found it; reading the source had not. "Groups" is in fact **ON by
   default**.
3. Also corrected in the pre-registration: R4/R4b's "all 64 edges are ring 2" — `SERVES`
   is ring 1, so 4 are.

### Rule Zero — screenshots inspected

`04_web_ch40_people_only.png` is the phase's real deliverable: **12 dots, zero lines**.
`03_web_ch40_default.png` opens focused on one character with ~17 dots and ~2 dozen
unlabelled lines; the side panel calls every tie "linked", never naming the relation.

### Verdict

- **R5 (LLM) still needed: YES.** Default-view edges at ch40 = 0, threshold 10. Two phases
  of grounding work moved it by zero.
- **Showable to a non-technical reviewer: NO, neither.** One reads as a broken app, the
  other cannot answer "how are these two related?".
- **Qualification:** the biggest ungrounded category is pronouns, which is coreference — a
  cheaper fix than R5. Weigh it before spending R5's budget.

### Gates

ruff clean · mypy clean · pytest green · C: checked against the ledger: **no new items**
(`.cache` still 135.76 MB; npm cache and playwright-core both on F:, `.local\pw` 12.8 MB).
