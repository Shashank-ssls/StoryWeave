# R8 — final evaluation of the v2 retrofit

| field | value |
| --- | --- |
| date | 2026-09-30 |
| branch | `retrofit/v2-core`, phase R8 |
| final DB | `data/retrofit/ninth_house_r6.db` (the R6/R7 state; R7 changed no data) |
| comparison DB | `evidence/v1_ninth_house.db` (frozen; served from a scratch copy, never written) |
| corpus | The Ninth House, 40 chapters |
| scope note | **No new pipeline run.** R8 was reduced for time: it evaluates the final state rather than rebuilding it. |

Every section below is labelled **[MEASURED]** or **[NOT MEASURED]**. Every number traces
to a script and a log named beside it.

---

## 0. The eight headline numbers — [MEASURED]

| # | quantity | v1 | final | source |
| ---: | --- | ---: | ---: | --- |
| 1 | fence violations | **0** / 105,243 | **0** / 28,869 | `tools/eval_fence.py`, `logs/R7_eval_fence.log` |
| 2 | relation micro-F1, **v1 key** | 0.0459 | **0.0000** | `tools/eval_score.py`, `logs/R8_score_final_v1key.log` |
| 3 | relation false positives, v1 key | 162 | **7** | same |
| 4 | entity F1, v1 8-type key | 0.5319 | **0.5682** | same |
| 5 | entity F1, 4-type key *(own key)* | — | **0.6250** | `logs/R8_score_final_proj.log` |
| 6 | alias F1 / over-merges *(own key)* | — | **0.7500** / **0** | same |
| 7 | default view at ch40 | 152 dots / 976 lines | **20 / 18** | `tools/r8_compare.py`, `logs/R8_compare.log` |
| 8 | median `/graph` at ch40 | 28.2 ms | **11.3 ms** | same |

The honest one-line summary: **the retrofit made the graph readable, the fence provable and
the false positives nearly disappear, and it did not make relation extraction work.**

---

## 1. What the system is — [MEASURED]

StoryWeave reads a novel and builds a graph of who is who and how they are connected, where
every node, edge and property carries the chapter at which a *reader* learns it. A query at
chapter *n* returns only what a reader at chapter *n* could know.

**It is zero-shot. Nothing here is trained, so there are no loss curves, no training set,
no held-out split, and no epochs to report.** The components are:

- **GLiNER** (zero-shot NER) for entities, prompted with the four drawable type names.
- **GLiNER-RelEx** (zero-shot relation extraction) prompted with the twelve closed relation
  names, plus a rule pass for structural relations.
- **qwen2.5:7b via Ollama**, local, temperature 0, as a recall pass that *proposes*
  relations. It never writes to the database directly.
- **A hand-written validator** that accepts or rejects every proposal against six checks.

The consequence for evaluation is that the three annotated chapters are an **answer key,
not a test split** — nothing was fitted to them, and nothing could be. It also means the
only levers are prompts, thresholds and rules, which is why every phase pre-registered its
expected band before scoring: with no training loop, the temptation to tune on the answer
key is the main threat to validity, and pre-registration is the only defence.

**The annotation itself is model-generated (GPT-5), hand-verified for indices and spans.**
Every score below is therefore *agreement between two systems*, not accuracy against human
ground truth. This is stated in the scorer's own banner and repeated here because it bounds
every F1 in this document.

---

## 2. v1 vs final, like-for-like only — [MEASURED]

Only four things can be compared directly. Everything else in this document is measured on
a key v1 was never scored against, and is reported in §3 instead.

### 2.1 The fence

| | v1 | final |
| --- | ---: | ---: |
| violations | **0** | **0** |
| elements inspected | 105,243 | 28,869 |
| queries issued | — | 12,660 |
| negative controls fire | yes | yes (12 and 198 detected) |

The element count fell because the default view is smaller, not because fewer surfaces are
checked: the final harness sweeps three surfaces v1 had no equivalent for (`/entity/{id}/ego`,
`/status`, and the salience ranking read directly). `DETECTOR VERIFIED TO FIRE: True` in both.

**A zero is only as good as its tested surface**, so: entities, graph nodes, graph edges,
node properties, node labels, entity detail, detail edges, detail properties, ego entity,
ego neighbours, status count, salience rank, arc names — every chapter 1–40.

### 2.2 Relation F1 on the original v1 answer key

| pooled, `chapter_local` | v1 | final |
| --- | ---: | ---: |
| true positives | 5 | **0** |
| false positives | 162 | **7** |
| false negatives | 46 | **51** |
| micro-F1 | 0.0459 | **0.0000** |

**The final system scores worse on this key, and the reason is not a regression.** R1
[MEASURED] that all five of v1's true positives came from the Tier-1 co-occurrence rule —
a rule that emitted 1,307 edges to catch 5, at a cost of 160 of the 162 false positives.
Deleting the rule deleted its 5 hits. What replaced it produces almost nothing on this key:
the final system's 7 false positives are real proposals that were wrong, not noise.

`cumulative` scope, same key: TP=0, FP=26, FN=51.

**Unmappable relations.** The v1 key uses v1's relation vocabulary; the final system emits
R4's twelve. Where a 1:1 mapping exists (`LocatedIn` → `LOCATED_IN`, `MemberOf` →
`MEMBER_OF`, `LeaderOf` → `LEADS`, `Serves` → `SERVES`, `Ally`/`Enemy` → `ALLY_OF`/`ENEMY_OF`,
the five identity relations → `SAME_AS`) it is applied. The reference relations that cannot
map at all, and are therefore unreachable on this key by construction, are `RelatedTo`
(v1's co-occurrence catch-all — deliberately abolished, retrofit rule 5), `HasAbility`,
`HasTitle`, `ParticipatedIn`, and `Respects`. In the three annotated chapters these account
for **19 of the 51 reference-side misses**.

### 2.3 What the client is handed

| chapter | v1 (all it had) | **final, default view** | final, "Everyone" |
| ---: | ---: | ---: | ---: |
| 10 | 71 dots / 363 lines | **10 / 4** | 86 / 33 |
| 20 | 104 / 556 | **14 / 8** | 134 / 43 |
| 40 | 152 / 976 | **20 / 18** | 191 / 99 |

v1 had **no display controls at all** — the cast filter was a client-side no-op (defect D3),
so one payload per chapter was the whole story. The final system's comparable figure is its
default view, because that is what a reader gets; "Everyone" is shown beside it so the
comparison cannot be accused of flattering the default by hiding the rest.

*A note on the v1 figures:* these are v1 restricted to the four drawable types, for
comparability. R0 [MEASURED] v1's genuinely unrestricted ch40 payload at **206 nodes /
1,316 edges**, which is the number to quote when the point is how much was being served.

### 2.4 Graph request time

Median of 15 calls, FastAPI TestClient, one process, no network.

| chapter | v1 | **final, default** | final, "Everyone" |
| ---: | ---: | ---: | ---: |
| 10 | 17.7 ms | **10.2 ms** | 12.7 ms |
| 20 | 20.6 ms | **10.7 ms** | 14.3 ms |
| 40 | 28.2 ms | **11.3 ms** | 16.9 ms |

v1's time grows with the chapter because its payload does; the final default view is
roughly flat because the cast dial bounds it. **This is not a production latency figure** —
it is the same measurement taken the same way on both systems, and that is all.

---

## 3. Final-only numbers, on their own keys — [MEASURED]

**These must never be reported as deltas against v1.** They are scored against projections
of the annotation that v1 was never measured on; a difference would be a difference of
answer key, not of system.

### 3.1 Entities, 4-type key

Pooled over chapters 9, 17, 37: **TP=25, FP=17, FN=13, P=0.5952, R=0.6579, F1=0.6250**.

| type | TP | FP | FN | F1 |
| --- | ---: | ---: | ---: | ---: |
| Character | 13 | 7 | 5 | 0.684 |
| Place | 9 | 5 | 3 | 0.692 |
| Organization | 3 | 1 | 4 | 0.545 |
| Item | 0 | 4 | 1 | 0.000 |

Item is the weak type and always has been: the four false positives are `ledger`,
`coin purse`, `certain goods` and one other generic object — exactly the strings the
reference's own `rejected_mentions` list says should not be entities. Pooled emitted-rate
on rejected strings: **4 of 49 (0.0816)**.

On the 8-type v1 key the same DB scores **F1 0.5682** (v1: 0.5319), which is the one entity
number that *is* a like-for-like comparison and is reported in §2 as such.

### 3.2 Aliases

**F1 0.7500 (P=1.0000, R=0.6000), over-merges 0, under-merges 2.**

Precision of exactly 1.0 with zero over-merges is the number that matters for a spoiler
product: an over-merge would fuse two identities the reader is supposed to discover
separately, which is the worst failure this system can commit. It has never occurred.

### 3.3 Salience

From `tools/r6_salience_score.py` (R6):

| metric | final | v1 (degree) | v1 after R1 |
| --- | ---: | ---: | ---: |
| P@10 | **0.8750** | 0.4000 | 0.3000 |
| P@20 | **0.8750** | — | — |
| MAP | **0.9033** | 0.4414 | 0.3668 |
| AUC | **0.6667** | — | — |

**The caveat that guts the headline, restated because it is easy to drop:** at chapters 17
and 37 *every* matched reference entity is flagged significant. With no negatives, AUC is
undefined there and P@k cannot score below 1.0 however the nodes are ordered. The pooled
0.8750 is carried by two chapters where the metric cannot discriminate; the only informative
chapter is **ch9, at P@10 0.6250 and AUC 0.6667**. Matched sets are 8, 10 and 7 nodes.

The honest reading: the ranking is clearly better than v1's on the same key, and the key is
far too small to say by how much.

Edge degree is deliberately **not** a feature — R1 measured v1's degree ranking collapsing
from P@10 0.4000 to 0.3000 the moment the co-occurrence edges were removed, and ranking a
cast by an extraction signal this weak would repeat that mistake.

---

## 4. The recall story, R4 → R5, and the pronoun bottleneck — [MEASURED]

This is the most important result in the retrofit and the one that took five phases to
isolate. Every relation the reference lists for the three annotated chapters was traced to
the stage that lost it.

| stage the relation was lost at | R4 | R4b | R4c | R5 |
| --- | ---: | ---: | ---: | ---: |
| out of scope (not one of the twelve) | 28 | 28 | 28 | 28 |
| `NO_PROPOSAL` — nothing was ever proposed | 12 | 18 | 18 | 17 |
| `ENTITY_MISSING` — an endpoint was never extracted | 6 | **0** | 0 | 0 |
| `WRONG_TYPE` | 2 | 2 | 2 | 2 |
| `VALIDATOR_REJECTED` | 1 | 1 | 1 | 1 |
| `GRADE_INFERRED` — found, but not STATED | 1 | 1 | 1 | **2** |
| found and served | 1 | 1 | 1 | 1 |

Read across the rows:

1. **R4** built real extraction from nothing and scored 0.0000. The bottleneck was traced
   to model recall, not to the validator: the validator rejected exactly **1** of the 51.
2. **R4b** fixed entity recall properly — a general head-noun rule for organisations, not a
   patch for the one missing gold entity — and eliminated `ENTITY_MISSING` entirely, 6 → 0.
   It recovered **zero relations**, because relex re-runs its own NER and never saw the
   improved entity set.
3. **R4c** grounded relex on the stored entities. `input_spans` turned out to be **accepted
   and then ignored** by the library (byte-identical output in both NER modes), so a
   span-snapping fallback was built instead. It moved 30 spans and recovered **zero**
   relations. The residue was then identifiable: **125 ungrounded endpoints are pronouns or
   common nouns** — `She` alone appears 14 times.
4. **R5** added the LLM. It found ring-1 social relations for the first time (ch40 ring-1
   edges 4 → 35), and the validator caught **5 invented relations and 3 paraphrased quotes**
   — the first non-zero values that column has ever had, which is the clearest evidence in
   the project that "the LLM proposes, the code disposes" is load-bearing. But **30 of the
   33 surviving edges graded INFERRED**, and the recall accounting moved by exactly **one**
   relation.

**The bottleneck is coreference, and it sits in the STATED rule.** Rule 4 requires the quote
to contain both participants' labels. English narrates a relationship with one participant
named and the other a pronoun — *"she had served the house since before the fire"* — so the
rule rejects a true, correctly-extracted relation because of a pronoun. R5 pre-registered a
diagnostic for exactly this ("how many INFERRED would be STATED if a named antecedent within
two context sentences counted") and **measured 2 of 33**, below its own 5–20 band, then did
**not** ship the loosening. The number is small because the LLM's recall is also small; the
two limits compound.

Neural coreference was probed earlier in the project and parked for library incompatibility.
It is the single highest-value piece of future work (§7).

---

## 5. Defects found and fixed — [MEASURED]

| id | defect | found | fixed in | evidence it is fixed |
| --- | --- | --- | --- | --- |
| **D1** | `nx.DiGraph` collapsed parallel edges before serialisation | R0 | R4 | ch40: **976 drawable rows → 976 payload edges** (was 1,326 → 1,316) |
| **D2** | `SECRET_IDENTITY` overwritten by a later edge on the same pair | R0/R1 | R4 | edge 1325 `SECRET_IDENTITY` and 1327 both reach the payload |
| **D3** | cast filter was a client-side no-op; status count was book-wide | R0 | R6/R7 | ch40 (20,18)/(28,24)/(53,27) for cast 20/50/all; status 17/86/191 at n=1/10/40 |
| **R6 regression** | `/graph` served **zero nodes** for any work with no salience ranking | R7 | R7 | `/graph?n=4` on the demo returned 0 nodes while `cast=all` returned 6; two tests now pin both halves of the rule |
| **8 UI defects** | camera never fitted · fitting it blanked every name · dial truncated · phone dialog unreachable, inert, undismissable · every `<input>` killed the keyboard · unconnected nodes clipped | R7 | R7 | tabulated in `R7_RESULT.md` §14 |

D3 is worth a sentence of its own: the status count told a chapter-1 reader how large the
cast eventually becomes. No name escaped, but a number did, and a number is a spoiler.

---

## 6. Threats to validity — [MEASURED] where counted, [NOT MEASURED] where stated

1. **The answer key is model-generated.** GPT-5 wrote it, one fresh session per chapter,
   single run each; indices and spans were hand-verified. Every F1 here is agreement between
   two systems. **[NOT MEASURED]:** no human ground truth exists for this corpus, and no
   inter-annotator agreement was computed because there is only one annotator.
2. **Three chapters, 51 relations, 46 entities.** At this size one relation is ~2 F1 points.
   Two of the three chapters have **no negative examples at all** for salience, which makes
   P@k uninformative there (§3.3).
3. **One corpus.** The Ninth House is the only novel with an annotation. The Hollow Crown is
   a seeded demo, not extraction output. **[NOT MEASURED]:** the universality spot check on
   Shadow Slave was not run — the text is not on this machine, which R2 also recorded.
4. **The corpus is synthetic.** The Ninth House was generated for this project, so its prose
   may be more regular than a published novel, which would flatter extraction.
5. **No new pipeline run in R8.** The final DB is R5's extraction plus R6's salience. Timing
   in §2.4 is request latency, not extraction throughput. **[NOT MEASURED]:** extraction
   time per chapter and peak RSS were not re-measured this phase.
6. **Scores are agreement at three chapters, but the fence is swept at forty.** The fence
   result is the strongest claim in this document precisely because its surface is large and
   its negative controls fire.
7. **Pre-registration was honoured but is self-administered.** Bands were committed before
   scoring and never edited — including the two R6 misses and R7's dots, which were left in
   place rather than re-fitted. An examiner has the commit hashes and can check.

---

## 7. Future work, in priority order — [MEASURED] basis for the ordering

1. **Pronoun/coreference resolution.** §4 shows this is *the* bottleneck. Every other
   recall fix in R4b and R4c recovered exactly zero relations because the endpoints that go
   missing are pronouns. Until "she" can be resolved to a name inside the quote, the STATED
   rule will keep rejecting true relations, and relation F1 will stay at zero.
2. **Widen the canvas before widening the ontology.** R7 measured that twenty names and
   thirteen relation labels do not both fit in the 652px the current three-column layout
   leaves. Reclaiming the right panel's 350px when nothing is selected is a small change
   with a large readability return.
3. **A bigger, human-checked answer key.** Everything in §3 is bounded by three chapters.
4. **Rank within the requested type set was done (R7); rank *stability* was not.** A reader
   moving one chapter forward should not see the cast reshuffle.
5. **A second corpus**, to separate "this system works" from "this system works on this
   novel".

---

## 8. Where the numbers come from

| number | script | log |
| --- | --- | --- |
| fence, final | `tools/eval_fence.py --db data/retrofit/ninth_house_r6.db` | `logs/R7_eval_fence.log` |
| relation + entity F1, v1 key | `tools/eval_score.py --db … --exclude-method curated` | `logs/R8_score_final_v1key.log` |
| entity 4-type, relation 12-relation, STATED | `tools/eval_score.py … --four-type-projection --twelve-relation-projection --grade stated` | `logs/R8_score_final_proj.log` |
| payload sizes + request timing | `tools/r8_compare.py` | `logs/R8_compare.log` |
| salience | `tools/r6_salience_score.py` | `logs/R6_salience_score.log` (R6) |
| recall accounting | `tools/r4_recall_audit.py` | R4/R4b/R4c/R5 result docs |
| UI counts + screenshots | `.local/pw/capture_r7.mjs` | `evidence/retrofit/shots/R7/capture_log.txt` |

CSV side-outputs: `evidence/retrofit/r8_scores_final_v1key.csv` (1,501 rows),
`evidence/retrofit/r8_scores_final_proj.csv` (794 rows).
