# R5 — local-LLM recall pass

| field | value |
| --- | --- |
| date | 2026-09-29 |
| branch | `retrofit/v2-core`, phase R5 |
| shipped DB | `data/retrofit/ninth_house_r5.db` (run B, clean few-shot) |
| sensitivity DB | `data/retrofit/ninth_house_r5_fewshotA.db` (run A, see §1) |
| model | `qwen2.5:7b`, temperature 0, `num_predict` 512, via stdlib `urllib` to local Ollama |
| models on disk | `.local\ollama_models` (4.47 GB) · cache `.local\llm_cache` · **nothing on C:** |
| validator | `extract/validator.py` **unchanged**, no bypass flag |
| pre-registration | `docs/retrofit/RETROFIT_PROGRESS.md`, commit `4aedbbb`, never edited |

Logs: `logs/R5_build_db.log`, `logs/R5_report.log`, `logs/R5_eval_score_*.log`,
`logs/R5_recall_audit.log`, `logs/R5_antecedent.log`, and the run-A set `logs/R5A_*.log`.
Every figure **[MEASURED]**.

---

## 0. Headline — all five pre-registered bands missed, stop condition hit

| quantity | pre-registered | measured (run B) | |
| --- | --- | ---: | --- |
| ring-1 edges at ch40, STATED | 5 – 25 | **4** | missed, just below |
| default-view edges at ch40 | 3 – 15 | **1** | missed |
| STATED micro-F1, 12-relation key | 0.05 – 0.30 | **0.0000** | missed |
| **STATED precision** | 0.50 – 0.90 | **0.0000** | **missed — STOP CONDITION** |
| antecedent diagnostic promotions | 5 – 20 | **2** | missed |

**STATED precision is 0.0000 (TP=0, FP=3), below the 0.5 floor, so the phase stops here
and reports. Nothing was tuned after this was seen.**

What R5 *did* change, and it is not nothing: **the graph has ring-1 social relations for
the first time in the entire retrofit.** MENTOR_OF 10, SERVES 12, ENEMY_OF 5, KIN_OF 3,
SAME_AS 2, KILLED 2, ROMANTIC_WITH 1 at chapter 40 — where R4c had four SERVES edges and
nothing else. But **only 4 of those 35 are STATED**, so the reader still sees almost none
of them.

---

## 1. The few-shot contamination, found and corrected — read this before §3

The first run's KIN_OF example was the real chapter-2 sentence *"Lord Fennick Oswald and
his sister Brenna Oswald sat nearer the door…"*. That obeys the pre-registered rule
(examples from chapters 2 and 13, outside the scored set {9, 17, 37}) — but
`Lord Fennick Oswald -Sibling-> Brenna Oswald` **is a gold relation at chapter 17**, so
the prompt named the exact pair the run was graded on.

It was re-run with that example replaced by a different chapter-2 pair
(Cassian / Ione Ashcombe), which also demonstrates resolving a pronoun to a named entity.
Everything else was identical. **Run A is kept whole as the sensitivity check.**

### What the comparison shows — [MEASURED]

| the ch17 gold relation `Fennick -Sibling-> Brenna` | run A (contaminated) | run B (clean) |
| --- | --- | --- |
| found by the LLM at all? | yes | **yes** |
| grade | **STATED** → served, counted FOUND | **INFERRED** → stored, not served |
| recall-accounting bucket | `FOUND` (2 total) | `GRADE_INFERRED` (2 total) |

**The example did not teach the model the relation — it taught the model the quote.** With
the example present, the model returned a quote naming both participants, which is what
STATED requires; without it, the model found the same relation but quoted a span that
names only one. So the discovery is genuine and reproducible; the *grade* was the
contaminated part, and with it run A's single true positive.

**Run B is the honest measurement and is what ships.** Run A's numbers appear in this
report only where they are labelled as such.

---

## 2. The run

```
candidates: 118 found, 118 after the cap (0 dropped)
calls: 118 live, 0 cached
raw LLM proposals: 83
edges added: 33 (33 graded)
grades: {'INFERRED': 30, 'STATED': 3}
total edges: 101 (44 STATED, 33 from the LLM)
```

The **per-chapter cap of 8 dropped nothing**, exactly as pre-registered: candidate counts
were measured before the cap was fixed (118 sentences, 39 chapters, max 6 per chapter), so
the cap is an overrun guard and never a filter. Wall clock ≈ 20 minutes, inside the 45
minute budget.

### Every LLM proposal outcome, by reason code — [MEASURED]

| reason | n | what it means |
| --- | ---: | --- |
| `ENDPOINT_NOT_STORED` | 12 | the model named something that is not a stored entity |
| `DOMAIN_RANGE` | 11 | e.g. a Character `MEMBER_OF` a Place |
| `KIN_GUARD` | 11 | kinship with no possessive attachment and no recurrence |
| `REINFORCED_EXISTING` | 5 | the pair+relation already existed; weight incremented |
| `RELATION_NOT_CLOSED` | 5 | the model invented a relation outside the twelve |
| `MALFORMED_JSON` | 3 | unparseable reply, discarded and logged |
| `QUOTE_NOT_VERBATIM` | 3 | the "quote" was not in the chapter text |
| `SELF_LOOP` | 3 | head and tail resolved to the same entity |
| **accepted** | **33** | 30 INFERRED, 3 STATED |

Two of these vindicate checks that had never fired before. `RELATION_NOT_CLOSED` = 5 and
`QUOTE_NOT_VERBATIM` = 3 were both **zero** for every relex run in R4/R4b/R4c; a
generative model is the first producer that invents relation names and paraphrases
quotes, which is precisely what those checks exist to stop. The validator was not relaxed
for the LLM and caught all eight.

---

## 3. Scores — [MEASURED]

Curated seeds excluded from every run (`--exclude-method curated`).

| run | key | grade | scope | TP | FP | FN | micro-F1 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| **headline** | 12-relation | STATED | chapter_local | 0 | 3 | 23 | **0.0000** |
| | 12-relation | STATED | cumulative | 0 | 10 | 23 | 0.0000 |
| diagnostic | 12-relation | STATED+INFERRED | chapter_local | 0 | 7 | 23 | 0.0000 |
| diagnostic | 12-relation | STATED+INFERRED | cumulative | **1** | 25 | 22 | **0.0408** |
| like-for-like | original v1 key | all | chapter_local | 0 | 7 | 51 | 0.0000 |

**STATED precision = 0 / (0 + 3) = 0.0000.** The three false positives are unchanged from
R4c (`Undercroft -LOCATED_IN-> Bone Market`, `Corwin -OWNS-> ledger`,
`Corwin -KIN_OF-> Hask`), i.e. **the LLM added no new STATED false positives** — it simply
added no STATED true positives either.

The one true positive anywhere is in the STATED+INFERRED cumulative cell, and it is an
INFERRED edge, which the graph does not serve. **Admitting INFERRED would cost heavily:
false positives rise 10 → 25 for that single true positive.** That is the measured answer
to "should we just show INFERRED edges": no.

### Recall accounting, R4c → R5 — [MEASURED]

| stage | R4c | **R5** | change |
| --- | ---: | ---: | :-- |
| `NOT_IN_THE_TWELVE` | 28 | 28 | — |
| `NO_PROPOSAL` | 18 | **17** | −1 |
| `ENTITY_MISSING` | 0 | 0 | — |
| `WRONG_TYPE` | 2 | 2 | — |
| `VALIDATOR_REJECTED` | 1 | 1 | — |
| `GRADE_INFERRED` | 1 | **2** | **+1** |
| `FOUND` | 1 | 1 | — |

One gold relation moved from `NO_PROPOSAL` to `GRADE_INFERRED`: the LLM found it, the
validator accepted it, and the both-names rule kept it off the screen. **That is the whole
of R5's effect on the answer key.**

*Caveat on this table:* `NO_PROPOSAL` vs `WRONG_TYPE` vs `VALIDATOR_REJECTED` is
classified against the **relex** proposal dump, so a gold relation the LLM never mentioned
still reads as `NO_PROPOSAL`. `FOUND` and `GRADE_INFERRED` come from the R5 database and
are exact.

---

## 4. Ring counts and the default view — [MEASURED]

| chapter | nodes | edges | ring1 | ring2 | STATED | INFERRED |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 86 | 33 | 13 | 20 | 13 | 20 |
| 20 | 134 | 43 | 17 | 26 | 17 | 26 |
| 30 | 153 | 70 | 25 | 45 | 31 | 39 |
| 40 | 191 | **101** | **35** | 66 | 44 | 57 |

Ring-1 at ch40, **4 → 35** against R4c. Per relation at ch40 (total / STATED):
`MENTOR_OF` 10/2, `SERVES` 12/1, `ENEMY_OF` 5/0, `KIN_OF` 3/1, `SAME_AS` 2/0,
`KILLED` 2/0, `ROMANTIC_WITH` 1/0, `ALLY_OF` 0/0.

**Default view at ch40 — Characters only, cast 20, STATED: 1 edge.** (R4c: 0.) With
INFERRED shown it would be 22, at the false-positive cost measured in §3.

---

## 5. The pre-registered diagnostic — measured, NOT shipped

"How many INFERRED proposals would become STATED under a *named antecedent within the 2
context sentences* rule?"

**2 of 33.** Pre-registered band was 5–20, so this also came in below. And the
promotions are not good ones — one is `Denna -SERVES-> Sorrel`, quoted from a sentence
about sorting a courtier's returned letters, which asserts no service relationship at all.

**Recommendation: do not build it.** It would buy two edges, at least one of them wrong,
in exchange for weakening retrofit rule 4 — the quote would no longer have to carry the
claim. The measurement is what makes that a decision rather than an opinion.

---

## 6. Acceptance checklist

- [x] `check_local_env.py` passes; C: byte-identical to the ledger after the whole run —
      `.ollama` 2,284 B and `%LOCALAPPDATA%\Ollama` 276,845 B **unchanged through 236
      model calls**; `.ollama\models` absent; no new C: item of any kind.
- [x] **Runs end-to-end with Ollama OFF.** Measured for real, not simulated: the server
      had died between sessions and the first re-run printed
      `OLLAMA UNREACHABLE — adding zero LLM edges, R4c graph left intact`, exit code 0.
- [x] Relation counts per type, R4c vs R5, with rejection reasons — §2, §4.
- [x] Every proposal through the unchanged validator; no bypass flag exists.
- [x] Responses cached in `.local\llm_cache`, keyed by (model, prompt hash).
- [x] Gates: ruff clean · mypy 75 files · pytest **287 passed, 6 skipped** (270 → 287,
      17 new LLM tests).
- [x] Stop condition honoured: precision 0.0000 < 0.5 → report, no tuning.

---

## 7. Verdict

**Default-view edges at ch40 = 1. The threshold for proceeding to R7 is 10. R7 must not
run next.** A reader opening the graph at chapter 40 would see twenty characters and one
line.

The binding constraint is now **isolated and named**: it is not entity recall (0 losses),
not the model's ability to find relations (it finds them — 83 proposals, 33 accepted,
35 ring-1 edges), and not the validator's type or closed-list checks. It is the **STATED
grade rule** — the requirement that one verbatim quote name both participants. 30 of 33
LLM edges fail exactly that test, and the corpus's prose keeps failing it because English
narration refers to one participant by pronoun.

Three options, in the order I would weigh them:

1. **Coreference.** R4c measured 125 ungrounded endpoints dominated by pronouns; R5 now
   shows 30 of 33 accepted edges graded INFERRED for the same reason. Both point at the
   same missing capability, and it is the only one that raises STATED without weakening
   rule 4. It was cut from the retrofit scope and parked for incompatibility.
2. **Widen what counts as "naming".** Let a quote satisfy the both-names rule when one
   side is a pronoun whose antecedent is the sentence's grammatical subject. Narrower and
   better-founded than the context rule §5 rejected.
3. **Change what ships.** Serve INFERRED edges with visibly weaker styling. Cheapest, and
   §3 prices it: false positives 10 → 25 for one true positive. I do not recommend it.

**This is a decision point, not a next phase.**

---

## 8. Viva defense

R5 is the phase where the LLM did its job and the pipeline still could not use the result.
It found relations the span model never could — 35 ring-1 edges where R4c had 4 — and 30
of 33 were filed INFERRED because the quote named only one participant, so the reader's
view moved from zero edges to one. The phase is defensible because every band was
committed in advance and all five were missed and reported as missed, and because the run
was thrown away and repeated the moment I noticed my own few-shot example named a pair
that was a gold answer; the re-run showed the example had been inflating the *grade*
rather than the discovery, which is a subtler and more useful finding than either the
contaminated number or a bare retraction. The validator earned its keep against a
generative producer for the first time — five invented relation names and three
paraphrased quotes, both categories that had never fired in three relex phases — and the
pre-registered diagnostic returned 2 promotions against a predicted 5–20, which is what
turns "should we relax the quote rule?" from an argument into a measurement.
