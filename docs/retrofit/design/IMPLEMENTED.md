# What the retrofit actually built

**Scope of this file.** `ARCHITECTURE.md`, `ONTOLOGY.md` and `EVALUATION_PLAN.md` in this
folder are the **v2 design**, written before any v2 code existed. The retrofit
(branch `retrofit/v2-core`, tag `retrofit-v1.0`) applied a **subset** of that design
*inside the v1 codebase* rather than building v2. This file is the map between the two, so
a reader of those three documents can tell, section by section, what is running and what is
only written down.

The three design documents are **not edited** to match what was built. A design document
that is quietly rewritten to agree with the implementation stops being evidence of anything.

**Status vocabulary**

| status | means |
| --- | --- |
| **built** | implemented as designed, in the shipped code |
| **changed** | implemented, but not the way the design specifies — the difference is stated |
| **deferred** | not built; still intended; the reason is usually a measurement |
| **cut** | not built and not planned; removed from scope by decision |

Phase commits: R0 `4ba8f80` · R1 `8319c46` · R2 `3b91545` · R3 `69a95e7` · R4 `f1204f0` ·
R4b `d31a43b` · R4c `b5469a2` · R5 `b60902b` · R6 `c372ac4` · R7 `a851fd3` · R8 `0366e4e`.
Two post-release frontend commits follow the tag: `53dd010`, `3b046b4`.

---

## 1. The headline

Four things a reader of the design docs should know before the tables:

1. **Events and the timeline were cut entirely.** `ONTOLOGY.md` §10 (Events) and
   `EVALUATION_PLAN.md` §5 describe a whole subsystem — event kinds, an event schema, a
   verifier, timeline salience. None of it exists, and R7 deleted the last v1 timeline
   remnants from the UI (grep proof in `R7_RESULT.md`). `Event` survives only as a legacy
   node type marked `NOT_A_NODE`.
2. **The death subsystem was deferred**, not cut. `ONTOLOGY.md` §9 and `ARCHITECTURE.md`
   §8's death case and cascade are unbuilt. What exists is the `KILLED` relation and its
   verb lexicon in `extract/cues.py` — the input the design's death logic would consume.
3. **Evidence grading shipped, then the shipping rule changed.** `ONTOLOGY.md` §12's
   STATED/INFERRED split is built. Retrofit rule 4 originally served STATED only; the R7
   amendment (user-approved 2026-09-29) serves **INFERRED too, drawn dashed and labelled
   "(implied)"**, because STATED-only left the ch40 default view at **1 edge across 20
   characters**. The measured price is in `R5_RESULT.md` §3: +1 true positive, +15 false
   positives.
4. **Coreference was deferred, and it is the measured bottleneck.** `ONTOLOGY.md` §13 puts
   coreference "off the critical path". R4c measured the opposite: of the ungrounded
   relation endpoints, **125 are pronouns or common nouns** (`She` x14). The thing the
   design treated as optional is the thing standing between the pipeline and recall.

---

## 2. `ONTOLOGY.md`

| § | Section | Status | Where / why |
| --- | --- | --- | --- |
| 0 | Why this document exists; four governing principles | **built** | The four principles survive as retrofit rules 1–9 in `CLAUDE.md`. |
| 1 | Text preparation (Stage 0) | **built** | R2 `3b91545`. 0 watermark hits / 0 homoglyphs over 44 chapters; injection round-trip 1,063 hits removed, 0 failures. §1.4's quotation-mark rule is honoured. |
| 2 | Node types (Character-only default; removals; attributes not types) | **built** | R3 `69a95e7`. Four types stored, Characters drawn by default, Ability/Concept/Event/Title never drawn. |
| 3 | The significance gate | **changed** | A gate exists, but salience rank (R6) is what actually decides the served cast, not §3's standard/unnamed-but-important paths. §3.3 overlay types are built as the Groups/Places/Items toggles. |
| 4 | Entity fields | **built** | R3. |
| 5 | Entity labels (kinds, display, abbreviation merge, late naming) | **built** | R3 `69a95e7`, `entity_labels` table. Alias F1 **0.7500** (P=1.0000, R=0.6000) with **0 over-merges**. |
| 6 | Relations — the twelve, rings 1 and 2 | **built** | R4 `f1204f0`. Closed list enforced in code; anything else rejected. |
| 6.2 | `KIN_OF` — directed | **changed** | Stored and served as directed. The design's *parent -> child* ordering is **not** derivable: `_possessive_kin` in `extract/validator.py` returns the kin noun with no binding to a participant, so `kin_role` does not say which endpoint is the parent. The arrow shows the stored source -> target ordering only (frontend `3b046b4`). |
| 6.3 | `KIN_OF` — the metaphor guard | **built** | R4, the kin guard: possessive attachment, or the claim repeated across two chapters. |
| 6.4 | `SAME_AS` versus alias | **built** | R4. `SAME_AS` is served **only when STATED** (R7 amendment guard 1). |
| 6.5–6.6 | Directional labels; label display by view | **built** | `R4_RELATION_LABELS` / `R4_RELATION_INVERSE`, drawn on every edge since R7. |
| 7 | Domain/range validator | **built** | R4, `DOMAIN_RANGE`. 44 `DOMAIN_RANGE` rejections at R4. |
| 8 | Edge fields; weight not duplicates; three chapter numbers | **built** | R4. Weight drives line thickness in 3 buckets. |
| 9 | **Death** (status, event, cascade, verb lexicon, rendering, resurrection) | **deferred** | Only §9.4's verb lexicon exists (`extract/cues.py`, the `KILLED` cue list). No `status` field, no cascade, no resurrection. |
| 10 | **Events** (kinds, schema, grading, verifier) | **cut** | No event table, no verifier. `NodeType.EVENT` is legacy-only, `LegacyTypeFate.NOT_A_NODE`. |
| 11 | The `revealed_chapter` invariant; fence surfaces | **built** | The strongest result in the project. Fence **0 violations / 28,869 elements** at R7, **0 / 105,243** on the frozen v1 DB, controls fire. One clause, in `query/fence.py` -> `db/repository.py`. |
| 12 | Evidence grading | **built, rule changed** | STATED/INFERRED both stored and now both served — see §1.3 above. |
| 13 | **Coreference** | **deferred** | The v2 method is unbuilt. A v1 "conservative self-reference merge" CLI (`storyweave coref`) exists and is **off unless a work opts in**. See §1.4 — this is the measured bottleneck. |
| 14 | Salience (features, combination, recency, rank not threshold, cast dial) | **built** | R6 `c372ac4`. P@10 **0.8750**, MAP **0.9033** vs v1 degree 0.4000/0.4414. The cast dial binds in SQL: ch40 (12,7)/(24,21)/(53,27) for 20/50/all, where v1's was a client-side no-op. **Caveat: AUC 0.6667 is defined at only 1 of 3 chapters.** |
| 15 | **Backbone extraction** | **cut** | No backbone code anywhere in `storyweave/`. Cut in the retrofit's opening scope decision. |
| 16 | Query layer | **built** | R6, the four-clause query: fence first, then cast, types, grade. |
| 17 | Extraction pipeline; model backends; empty results | **changed** | GLiNER + relex + an optional local LLM (R5) are built. §17.1's ONNX backend is **cut** — no ONNX anywhere. |
| 18 | Frontend | **built** | R7 `a851fd3`, plus `53dd010` and `3b046b4` after the tag. ch40 default: 20 dots / 18 lines, all 20 names legible. |
| 19 | Out of scope for v2 | n/a | Still out of scope. |
| 20 | Validation corpus | **built** | The Ninth House, 40 chapters, `data/retrofit/ninth_house_r6.db`. |
| 21 | Open items; Appendix A decision log | n/a | Superseded by `RETROFIT_PROGRESS.md`. |

---

## 3. `ARCHITECTURE.md`

| § | Section | Status | Where / why |
| --- | --- | --- | --- |
| 1–3 | What the system does; why v2 exists; system overview | **built** | The v1 failure in §2 is the retrofit's whole justification, and its numbers are the ones R0 re-measured. |
| 4 | Stage 0 — text normalisation | **built** | R2 `3b91545`. |
| 5 | Extraction pipeline | **changed** | Built without the ONNX path (§17.1 above). |
| 6 | The validator; domain/range; `KIN_OF`; evidence grading | **built** | R4 `f1204f0`. First non-zero catches at R5: 5 invented relations, 3 paraphrased quotes. |
| 7 | Data model; weight not duplicates; labels are a table | **built** | R3 + R4. |
| 8 | The three chapter numbers | **built** | |
| 8 | ...the **death case** and **death cascade** | **deferred** | See ONTOLOGY §9. |
| 9 | Query layer; **salience** | **built** | R6 `c372ac4`. |
| 9 | Query layer; **backbone** | **cut** | See ONTOLOGY §15. |
| 10 | What the reader sees | **built** | R7 `a851fd3`. |
| 11 | Deliberate exclusions; scope boundaries | n/a | Retrofit cut more: see §1. |
| 12 | Questions for the reviewer | n/a | Several are now answered by measurement; see `EVAL_RETROFIT.md`. |
| 13 | Glossary | n/a | |

---

## 4. `EVALUATION_PLAN.md`

This document was **written before the retrofit but committed only now** (2026-09-30), in
this same commit. R8 flagged it as missing from the repository — see
`PROJECTION_CHECK.md` §0. It is therefore a pre-registration that was **not** under version
control while the measurements it governs were being taken. That is a real weakness in the
audit trail and is recorded rather than glossed: the honest claim is "written first, filed
late", not "pre-registered in the repo".

| § | Section | Status | Where / why |
| --- | --- | --- | --- |
| 0 | Why this is written first; reporting rules | **built** | §0.1's MEASURED / PREDICTED / PROJECTED labelling is retrofit rule 9 and is used throughout `evidence/retrofit/`. |
| 1 | Ground truth (corpus, chapter selection, annotation, consistency, disagreements) | **changed** | A single-annotator gold set at ch9/20/40 exists (`evidence/annotation/`). §1.4's inter-annotator consistency check was **not** run — one annotator, so §1.5's "disagreements are the primary output" has no second opinion to disagree with. |
| 2 | Metric summary | **built** | `EVAL_RETROFIT.md`. |
| 3.1 | Entity detection | **built** | 4-type F1 **0.6250**; v1-key like-for-like **0.5319 -> 0.5682**. |
| 3.2 | The significance gate | **changed** | Measured as salience ranking quality (§6), not as the design's gate. |
| 3.3 | Alias clustering | **built** | F1 **0.7500**, over-merges **0**. |
| 3.4 | Coreference | **deferred** | Nothing to measure; see §1.4. R4c's 125-ungrounded-endpoint diagnostic is the closest thing. |
| 4.1 | Relation metrics per type | **built** | And the answer is the project's central negative result: STATED micro-F1 **0.0000**, TP **0**. |
| 4.2 | `KIN_OF` metaphor guard | **built** | |
| 4.3 | `SAME_AS` — counts, never F1 | **built** | Counted, never F1'd, as specified. |
| 4.4 | **Death and killer attribution** | **cut** | No death subsystem to measure. |
| 4.5 | Evidence grading | **built** | R5 §3's STATED vs STATED+INFERRED table is exactly this metric, and it priced the rule-4 amendment. |
| 5 | **Events** (per kind, shipping rule, timeline salience) | **cut** | |
| 6 | Salience ranking (ground truth, metrics, ablation, weight tuning) | **changed** | P@10 and MAP built; §6.3's ablation and §6.4's weight tuning **not** run. §6.4's own caveat about tuning on the evaluation set is why. |
| 7 | The spoiler fence (leak rate, non-vacuous zero, surface coverage) | **built** | The one section delivered in full, including §7.2: the zero is reported **with its tested surface** and with controls that fire. |
| 8 | Graph readability (metrics, configurations, growth curves, caveat) | **built** | R7. §8.5's comprehension pilot was optional and **not** run. |
| 9.1 | ONNX parity | **cut** | No ONNX. |
| 9.2 | Performance | **changed** | `/graph` latency measured (ch40 median **28.2ms -> 11.3ms**). Extraction throughput and peak RSS are **[NOT MEASURED]** — R8 cut the pipeline re-run for time and says so rather than estimating. |
| 10 | Universality (Stage 0 effectiveness, scope statement) | **changed** | Stage 0 measured on the Ninth House only. Shadow Slave is **[NOT MEASURED]** — the text is not on this machine. |
| 11 | Threats to validity | **built** | Carried into `EVAL_RETROFIT.md`. |
| 12 | Report structure | **built** | |
| 13 | What is decided by measurement | **built** | Two stop conditions fired (R4, R5); both were honoured. |

---

## 5. What is deferred, in the order it should be picked up

1. **Coreference** — R4c measured it as the bottleneck. Nothing else in the relation
   pipeline is worth tuning until pronoun endpoints can be grounded.
2. **The death subsystem** — designed in full, unbuilt, and it depends on nothing that is
   missing.
3. **Backbone extraction** — cut for scope, not for a measured reason.
4. **Events and the timeline** — cut, and should stay cut until relations work: an event
   subsystem built on an extractor with 0 true-positive relations would inherit the problem.
5. **ONNX** — an engineering convenience with no bearing on any open question.
