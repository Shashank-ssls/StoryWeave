# R4 — twelve closed relations, the validator, weight, and the D1/D2 fix

| field | value |
| --- | --- |
| date | 2026-09-29 |
| branch | `retrofit/v2-core`, phase R4 (R0–R3 complete) |
| output DB | `data/retrofit/ninth_house_r4.db`, built by `tools/build_r4_db.py` from `ninth_house_r3.db` |
| model | `knowledgator/gliner-relex-base-v1.0`, CPU, from `F:\Dev\shared\hf-cache`, `HF_HUB_OFFLINE=1` |
| LLM | off. No Ollama, no API, nothing downloaded |
| frozen DB | never written. SHA-256 `C7264C16…D946FF`, 847,872 bytes, still read-only — re-verified |
| pre-registration | `docs/retrofit/RETROFIT_PROGRESS.md`, commit `d99e445`, written before the first scoring run |

Logs, verbatim: `logs/R4_build_db.log`, `logs/R4_eval_score_stated.log`,
`logs/R4_eval_score_all_grades.log`, `logs/R4_eval_score_v1key.log`,
`logs/R4_recall_audit.log`, `logs/R4_curated_check.log`, `logs/R4_eval_fence.log`,
`logs/R4_local_env.log`. Every figure below is **[MEASURED]**.

> Scores are **agreement** with a model-generated (GPT-5) reference annotation with
> hand-verified indices, not accuracy against human ground truth
> (`evidence/annotation/PROVENANCE.md`).

---

## 0. The headline, stated plainly

**STATED-only relation micro-F1 on the 12-relation key: 0.0000. TP=0, FP=3, FN=23.**

```
--- pooled [chapter_local] --- TP=0 FP=3 FN=23
  micro P=0.0000 R=0.0000 F1=0.0000   macro-F1 over 5 relation types: 0.0000
```

**The pre-registered band was 0.05 – 0.20. The measured value is below it, and below the
phase's 0.05 stop condition.** Per the stop rule the validator was NOT loosened to
rescue the number; nothing about the cue lists, the threshold or the kin guard was
changed after this was seen. R4 stops here and reports.

R4 did build a real relation extractor where R1 left none — 64 edges, 37 of them STATED,
every one carrying a verbatim quote — but **none of them is one of the 23 relations the
answer key asks for in the three scored chapters.** Section 5 says exactly why, per gold
relation, and that table is the real output of this phase.

---

## 1. What was built, in numbers

`306 proposals → 64 edges (+61 reinforcements), 181 rejected` — `logs/R4_build_db.log`,
verbatim:

```
relations : work id=1: 306 proposals -> 64 edges (+61 reinforcements), 181 rejected.
            [LEADS:2, LOCATED_IN:20, MEMBER_OF:22, OWNS:16, SERVES:4]
            grades [INFERRED:31, STATED:33]
edges     : 64 total, 37 STATED
```

(The per-grade counts in the builder line are counted at INSERT; the final 37/27 split
below includes reinforcements that later upgraded an edge from INFERRED to STATED.)

| relation | STATED | INFERRED | total |
| --- | ---: | ---: | ---: |
| LOCATED_IN | 20 | 0 | 20 |
| MEMBER_OF | 6 | 16 | 22 |
| OWNS | 10 | 6 | 16 |
| SERVES | 1 | 3 | 4 |
| LEADS | 0 | 2 | 2 |
| KIN_OF, ROMANTIC_WITH, ALLY_OF, ENEMY_OF, MENTOR_OF, KILLED, SAME_AS | 0 | 0 | **0** |
| **total** | **37** | **27** | **64** |

**Every single edge is ring 2.** The seven ring-1 social relations — the ones the default
graph is supposed to draw — got zero edges. That is the most important fact in this
table: R4 produced an overlay and no graph.

Weight works as designed (R4 task 5): 64 rows carry 125 units of evidence, so 61 repeat
observations were folded into existing rows instead of becoming duplicate edges.
Distribution: weight 1 × 36, 2 × 18, 3 × 2, 4 × 3, 5 × 3, 10 × 2.

### Rejections by reason — [MEASURED]

| reason | n | share of 181 |
| --- | ---: | ---: |
| `ENDPOINT_NOT_STORED` | 137 | 75.7% |
| `DOMAIN_RANGE` | 44 | 24.3% |
| `QUOTE_NOT_VERBATIM` | 0 | 0% |
| `RELATION_NOT_CLOSED` | 0 | 0% |
| `SELF_LOOP` | 0 | 0% |
| `KIN_GUARD` | 0 | 0% |

Two of these zeros are worth reading carefully, because a zero is only meaningful with
its tested surface (retrofit rule 9):

* **`QUOTE_NOT_VERBATIM` = 0 over 306 proposals** is not evidence that check (a) is
  toothless — it is evidence that quote construction is correct by construction. Quotes
  are literal slices of `chapters.clean_text` expanded to sentence boundaries, so they
  cannot fail to be verbatim. The check is doing real work against *future* producers
  (R5's LLM, where a paraphrased quote is the expected failure), and it is exercised by
  two unit tests, one of which puts the right words in the wrong chapter.
* **`KIN_GUARD` = 0** because relex proposed **no** kinship pair that survived grounding
  — not because the guard passed everything. The guard is exercised by five unit tests
  including both of the cases the R4 brief names by hand, and it refuses one of the 19
  curated edges (§4).

---

## 2. The two scores, and the like-for-like run

All three runs exclude the hand-curated seed edges (`--exclude-method curated`).

| run | key | grade | TP | FP | FN | micro-F1 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| **headline** | 12-relation projection | STATED only | 0 | 3 | 23 | **0.0000** |
| diagnostic | 12-relation projection | STATED + INFERRED | 0 | 3 | 23 | 0.0000 |
| like-for-like | original v1 key | all | 0 | 3 | 51 | 0.0000 |

`cumulative` scope, same order: FP 3 / 16 / 16, FN 23 / 23 / 51, F1 0.0000 throughout.

**What the STATED rule costs in recall: nothing, measured.** The diagnostic run is
identical to the headline on `chapter_local` — admitting INFERRED edges adds no true
positives and no false negatives, only false positives in the cumulative scope (3 → 16).
So the "both names in the quote" rule is not what is holding recall down here. That was
worth measuring precisely because it was the obvious suspect, and it is exonerated.

**The v1-key run is like-for-like with R0/R1** (same scorer, same key, no flags beyond
the curated exclusion): micro-F1 0.0000, unchanged from R1's 0.0000, with FP 2 → 3 and
FN 51 → 51.

### The unmappable gold relations

The 12-relation projection maps 23 of the 51 gold relations and drops 28. Dropped, with
their fate from `LEGACY_RELATION_MAP` — these have no 1:1 target and are therefore
absent from the 12-relation key by design:

| old relation | fate | n |
| --- | --- | ---: |
| `RelatedTo` | DROPPED (the never-drop co-occurrence fallback) | 11 |
| `HasTitle` | BECOMES_LABEL (an `entity_labels` row, scored by R3) | 6 |
| `HasAbility` | DROPPED (Ability is not a drawable type after R3) | 3 |
| `ParticipatedIn` | DROPPED (Event is not a drawable type after R3) | 3 |
| `AffiliatedWith` | DROPPED (ambiguous between ALLY_OF and MEMBER_OF) | 2 |
| `Respects` | DROPPED (outside the closed twelve) | 2 |
| `Protects` | DROPPED (outside the closed twelve) | 1 |
| **total dropped** | | **28** |

Per-chapter: ch09 13 mapped / 8 dropped, ch17 6 / 12, ch37 4 / 8.

**54.9% of the answer key is outside what the retrofit will ever produce.** That is a
consequence of retrofit rules 2 and 3, not a defect, but it means the 12-relation key is
a materially different and smaller key than v1's, and its F1 must never be quoted as a
delta against 0.0459.

---

## 3. Where the cue lists, the threshold and the kin guard came from

Integrity rule 2: all three were fixed **before** the first scoring run and without
reading the annotation's gold relations or evidence quotes.

| knob | value | source |
| --- | --- | --- |
| cue words, 12 lists | `storyweave/extract/cues.py` | **`docs/ONTOLOGY.md` does not exist in this repository.** SPEC.md §5.3 is the ontology of record and was used in its place, together with the natural-language prompts already in `nlp/relex.py` since Phase 7a, plus a hand thesaurus pass for general English synonyms. The substitution is recorded in the module docstring, not glossed. |
| relex relation threshold | **0.6** | `Settings.relex_rel_threshold`, the already-configured default. Unchanged. |
| relex NER threshold | **0.3** | `Settings.relex_ner_threshold`, the already-configured default. Unchanged. |
| kin guard | possessive genitive OR ≥2 chapters, similes refused | written from the two cases the R4 brief names, both of which are in the phase prompt, not the answer key. |

**No threshold sweep was run**, so there is no diagnostic sweep table to report and no
risk of a shipped value having been selected from one. Per-work cue overrides exist as a
`[relations.cues]` knob in `storyweave.toml` and **are empty** for this work — the
shipped run used the defaults exactly as written.

One precision risk was recorded in the cue module **in advance** rather than discovered
afterwards: LOCATED_IN's cue list contains bare prepositions ("in", "at", "from"),
because that is how English states location. For that one relation the cue test is weak
and the both-names test carries the burden. It was not tuned away after seeing the score.

---

## 4. The curated seeds, kept out of the score

The 19 hand-curated edges in the frozen baseline are **not** extraction output and are
excluded from every number in §2 via `--exclude-method curated`. The R4 database contains
**zero** curated edges (all 64 are `gliner`), so the exclusion is belt-and-braces there.

Run through the same validator (`tools/r4_curated_check.py`, `logs/R4_curated_check.log`):

| verdict | n |
| --- | ---: |
| ACCEPT (INFERRED) | 11 |
| ACCEPT (STATED) | 1 |
| NOT_IN_THE_TWELVE (DROPPED: Rival, Protects, Respects) | 3 |
| NOT_IN_THE_TWELVE (BECOMES_LABEL: 2 × ALIAS) | 2 |
| REJECT (KIN_GUARD) | 1 |
| REJECT (QUOTE_NOT_VERBATIM) | 1 |
| **total** | **19** |

**12 of 19 would be accepted, but only 1 as STATED.** The two individual refusals:

* `Meraude -Parent-> Sable Vell` — `KIN_GUARD`: the stored evidence has no possessive
  attachment and the claim appears in one chapter only.
* `Thessaly -Mentor-> Mira` — `QUOTE_NOT_VERBATIM`: the stored `evidence_span` is not
  found in the clean text of chapter 7. This is a real finding about the curated data,
  not about the validator: a hand-written citation that does not appear in the book.

Caveat, stated rather than left implicit: the frozen baseline predates R3 and has **no
`entity_labels` table**, so this check sees only `nodes.name` for each endpoint. The
STATED rate of 1/12 is therefore a floor — with R3's aliases available, more of these
quotes would name both participants.

---

## 5. Recall accounting — where each of the 51 gold relations was lost

This is the table the R4 brief calls the phase's most important output.
`tools/r4_recall_audit.py`, `logs/R4_recall_audit.log`. Stages are tested in order, so
each gold relation lands in exactly one bucket and the buckets sum to 51.

| stage | n | share |
| --- | ---: | ---: |
| `NOT_IN_THE_TWELVE` — outside the closed list by design | 28 | 54.9% |
| `NO_PROPOSAL` — endpoints exist, relex proposed nothing for the pair | 12 | 23.5% |
| `ENTITY_MISSING` — R3 never created an endpoint | 6 | 11.8% |
| `WRONG_TYPE` — relex proposed the pair with a different relation | 2 | 3.9% |
| `VALIDATOR_REJECTED` | 1 | 2.0% |
| `GRADE_INFERRED` — validated but not STATED, so not served | 1 | 2.0% |
| `FOUND` — present in the shipped STATED graph | 1 | 2.0% |
| **total** | **51** | |

### Reading it

1. **Over half the key is out of scope by construction** (28/51). The retrofit refuses to
   create `RelatedTo`, `HasAbility`, `ParticipatedIn`, `AffiliatedWith`, `Respects`,
   `Protects`, and turns `HasTitle` into a label. Nothing in R4 or R5 will recover these,
   and nothing should.
2. **The single biggest *fixable* loss is `NO_PROPOSAL`** (12/51, 23.5%) — both entities
   exist in the graph, and relex simply did not relate them. Nine of the twelve are
   `LocatedIn` or `MemberOf` on pairs the text states plainly ("Casimir Lowe took the
   eastern docks", "Lord Fennick Oswald" ↔ "House Oswald"). This is a model-recall
   problem, which is exactly what R5's LLM pass exists for.
3. **`ENTITY_MISSING` is 6/51, and all six are the same entity** — `Salt Quarter watch`,
   an Organization R3 never created. One missing entity costs six relations. Entity
   recall and relation recall are not independent, and the cheapest relation win
   available is an entity fix.
4. **The validator is not the bottleneck.** Exactly one gold relation reached it and was
   refused (`Hask -Serves-> House Vell`, `DOMAIN_RANGE`: SERVES is C → C,O and R3 typed
   `House Vell` as a Place, not an Organization — a *type* error surfacing as a relation
   loss). One more was validated but graded INFERRED.

### The discrepancy between this table and the scorer — stated, not hidden

The audit finds **1 FOUND** (`ch37 Mira Quell -LocatedIn-> Undercroft`) while the scorer
reports **TP=0**. Both are correct; they use different matching:

* the audit resolves gold entity names through R3's `entity_labels`, so `Mira Quell`
  resolves to the node the graph calls `Mira`;
* the scorer's relation match requires both endpoints to have matched under **its own**
  entity-match rule, which is strict on the canonical name, and it reports
  `Mira Quell … not found by v1`.

**The headline number is the scorer's 0.0000**, because that is the number that is
like-for-like with R0 and R1. The audit's 1 is reported here as what it is: one gold
relation that is genuinely present in the shipped graph and that the scorer's strict
endpoint rule does not credit. It is not counted as a true positive anywhere.

---

## 6. D1 and D2 — fixed, with regression tests

The payload no longer passes through `nx.DiGraph`. `graph/serialize.py:graph_json` builds
the Cytoscape payload **directly from the fenced rows**, so one fenced drawable row in is
exactly one payload edge out, by construction rather than by luck. `build_graph` still
exists for analysis callers and now returns a `MultiDiGraph`, so even that path stops
losing rows.

Regression tests, on the **frozen** baseline (copied, chmod'd writable, never migrated —
the copy has no R4 columns, which makes this also the pre-R4-database-still-serves test):

* `test_d2_the_secret_identity_edge_reaches_the_payload` — edge **1325 `SECRET_IDENTITY`**
  (pair 14 → 150) and edge **1327 `REINCARNATION`** both reach the payload, each with its
  own relation string. Under v1, 1325 was overwritten by 1327 and the identity reveal was
  destroyed.
* `test_d1_payload_edge_count_equals_fenced_drawable_row_count` — parametrised over
  chapters 1, 5, 9, 17, 25, 37, 40: payload edge count equals fenced drawable row count,
  and the *sets* of edge ids are equal, so the test cannot be satisfied by a coincidence
  of counts.

**D1 at ch40 on the frozen DB, measured: 1326 rows pass the fence; 976 of those are
DRAWABLE (both endpoints one of R3's four types); the payload serves 976.** Row count in
== payload count out, and the id sets are equal — the projection layer now loses nothing.

The two reductions must not be confused, so both are named: 1326 → 976 is **R3's display
filter**, a deliberate narrowing of what is drawn, applied after the fence and separately
from it (retrofit rule 1). The D1 defect was the *other* loss — 1326 → 1316 under v1,
where ten rows were silently overwritten inside `nx.DiGraph`. That loss is now zero, and
edge 1325 is among the rows that survive.

---

## 7. Controls

| control | result |
| --- | --- |
| fence, R4 database | **0 violations over 24,450 elements**; both negative controls fire (`DETECTOR VERIFIED TO FIRE: True`, sabotaged run detects 188) |
| frozen DB | SHA-256 `C7264C16…D946FF`, 847,872 bytes, `IsReadOnly = True` — matches `evidence/BASELINE.md` |
| Hollow Crown | seeded data unchanged; digest test still asserts the original `e73a69c0…c482` (see the I2 note below) |
| entities | untouched by R4 — 188 entities, inherited from `ninth_house_r3.db` |
| C: drive | `.cache` 135.8 MB (unchanged from the R0 baseline); pip / Ollama / Playwright still absent. Nothing downloaded |
| gates | `ruff check .` **All checks passed!** · `mypy` **Success: no issues found in 66 source files** · `pytest` **253 passed, 6 skipped** (221 → 253, 32 new) |

### Two deviations, stated not buried

1. **The Hollow Crown digest test now names its columns instead of `SELECT *`.** R4 adds
   seven additive columns to `edges`, so `SELECT *` would change the digest without a
   single seeded value changing — it was pinning the *width of the schema*, not the
   contents of the fixture. The column list is spelled out and **the expected hash is
   unchanged**: it is still the value recorded before any R3 code was written, so if any
   seeded datum had moved, the test would still fail. This is the minimum change that
   keeps rule I2's actual guarantee intact.
2. **The unique index on `(work_id, relation, source_id, target_id)` is PARTIAL**, scoped
   to `WHERE grade IS NOT NULL` — i.e. to rows this retrofit's validator wrote. A full
   index broke the Phase-7d coref merge, which legitimately re-points an edge onto a pair
   that already carries the same relation at a different tier. The uniqueness claim is a
   claim about R4's producer, and the constraint now says exactly that instead of
   silently breaking a working legacy path.

---

## 8. What R4 changed in the code

| file | change |
| --- | --- |
| `storyweave/db/models.py` | `Relation` (12), `DOMAIN_RANGE`, `RelationGrade`, `RING1/RING2`, `LEGACY_RELATION_MAP` with an import-time assert that every stored relation has a recorded fate; seven new `Edge` fields, all defaulted |
| `storyweave/db/repository.py` | 7 additive edge columns + `validator_rejections` + the partial unique index; `migrate_edges_r4`, `migrate_edges_relation_vocabulary` (create-copy-drop-rename, ids preserved), `has_edge_r4_columns` probe; `get_edge_by_relation_pair`, `reinforce_edge`, rejection logging |
| `storyweave/extract/cues.py` | the 12 cue lists, with their provenance in the docstring |
| `storyweave/extract/validator.py` | checks (a)–(f), one reason code each; no SQL, no database |
| `storyweave/extract/relations.py` | the producer: propose → two-pass (kin guard is non-local) → dispose → weighted upsert |
| `storyweave/nlp/relex.py` | span offsets (so a quote can be a literal slice); `R4_RELATION_PROMPTS`; an explicit prompt set, defaulting to the untouched Phase-7a behaviour |
| `storyweave/graph/serialize.py` | payload built from rows; `build_graph` → `MultiDiGraph` |
| `tools/` | `build_r4_db.py`, `r4_recall_audit.py`, `r4_curated_check.py`; `eval_score.py` gains `--twelve-relation-projection`, `--grade`, `--exclude-method` (all default to the v1 behaviour) |

---

## 9. Viva defense

R4's honest result is that it built a working relation extractor and scored zero, and the
report leads with that instead of with the 37 cited edges it could have led with. The
phase is defensible anyway because it was pre-registered: the expected band (0.05–0.20)
was committed before the first run, the cue lists and threshold were fixed without
reading the answer key, the curated seeds were held out, and when the number came in
under the stop condition nothing was loosened to rescue it. The value delivered is the
recall-accounting table, which converts "F1 = 0" into four separately actionable numbers:
28 of 51 gold relations are out of scope by design, 12 are pure model-recall misses that
R5 is aimed at, 6 are all downstream of one missing Organization, and exactly 1 reached
the validator and was refused — so the validator is provably not the bottleneck, and the
next day of work belongs to entity recall and the LLM pass, not to the gate. D1/D2 are
separately and genuinely fixed: the `SECRET_IDENTITY` reveal that v1 silently overwrote
now reaches the payload, pinned by a set-equality test at seven chapters.
