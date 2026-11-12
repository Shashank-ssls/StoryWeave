# R4b — Organization recall: fixing the class, and measuring what that buys

| field | value |
| --- | --- |
| date | 2026-09-29 |
| branch | `retrofit/v2-core`, phase R4b (small, inserted after R4) |
| entities DB | `data/retrofit/ninth_house_r4b_entities.db` (re-extraction, all 40 chapters) |
| relations DB | `data/retrofit/ninth_house_r4b.db` (R4 relex + validator, **settings unchanged**) |
| models | `urchade/gliner_small-v2.1` + `knowledgator/gliner-relex-base-v1.0`, CPU, `HF_HUB_OFFLINE=1` |
| LLM | off. No Ollama, no API |
| frozen DB | never opened for writing |
| gold annotation | **never opened during diagnosis or fix design** — see §0 |

Logs: `logs/R4b_diagnosis.log`, `logs/R4b_prompt_probe.log`, `logs/R4b_build_entities.log`,
`logs/R4b_build_db.log`, `logs/R4b_recall_audit.log`, `logs/R4b_eval_score_stated.log`,
`logs/R4b_entity_before.log`, `logs/R4b_entity_after.log`. Every figure is **[MEASURED]**.

---

## 0. The headline

**The general fix works at the entity layer and recovers ZERO of the six relations.**

| | R4 | R4b |
| --- | ---: | ---: |
| `ENTITY_MISSING` (recall-accounting stage) | 6 | **0** |
| `NO_PROPOSAL` | 12 | **18** |
| relation micro-F1, STATED, 12-relation key | 0.0000 | **0.0000** |
| entity F1, 4-type key, strict | 0.6076 | **0.6250** |
| Organization F1, 4-type key, pooled | 0.400 | **0.545** |
| alias over-merges | 0 | **0** |

The `ENTITY_MISSING` stage is **eliminated** — all six of those gold relations now have
both endpoints in the graph. They did not become true positives. They moved one stage
downstream into `NO_PROPOSAL`, and the relation score did not move at all.

**This is reported as a partial success, and the rule was NOT narrowed to make it look
better.** §5 explains why the bottleneck moved rather than cleared, which is a more useful
finding than a recovered point of F1 would have been.

---

## 1. Diagnosis — from the text, never from the gold file

`tools/r4b_org_diagnosis.py` reads only the corpus and the R3 database. It asks three
questions in order, which localise the fault to exactly one stage.

**The class is small, and that is itself a finding.** Across all 40 chapters there are
42 group-noun phrases, 15 distinct; only **5** have the shape of a named body (a
capitalised modifier in front of the group noun), and each occurs **once**:

| phrase | mention emitted by the GLiNER floor? | became a node? |
| --- | --- | --- |
| `Ashcombe household` | yes, Organization | yes |
| `The Regent's household` | yes, Organization | yes |
| `The chancery` | yes, Organization | yes |
| **`Salt Quarter watch`** | **no mention at all** | no |
| **`Cassian's guard`** | **no mention at all** | no |

**The fault is upstream of everything the graph layer does.** For the two missed phrases
GLiNER emitted no mention, so no significance rule, no merge rule and no four-type write
check ever saw them. Of the four candidate causes in the brief — label prompt, threshold,
significance/merge rules, four-type write check — the last two are **excluded by
measurement**, not by argument.

The specific failure is **nested-span preference**: asked about "the Salt Quarter watch",
GLiNER returns `'Salt Quarter' -> Place` and stops. It found something, and what it found
is a Place strictly inside the organization's name.

---

## 2. The label prompt is not the fix — measured, not assumed

Before writing a rule, the cheaper option was tested. `tools/r4b_prompt_probe.py` runs the
floor over every sentence in the corpus containing such a phrase, once per candidate
prompt set. All candidates are general English descriptors of a collective; none names
anything in this book.

| label set | `Salt Quarter watch` | `Cassian's guard` | class recovered? |
| --- | --- | --- | --- |
| shipped R3 set | `'Salt Quarter'->Place` | MISSED | no |
| + `"group of people"` | `'Salt Quarter'->Place` | MISSED | no |
| + `"military unit"` | `'Salt Quarter'->Place` | MISSED | no |
| + `"institution"` | `'Salt Quarter'->Place` | MISSED | no |
| + all three | `'Salt Quarter'->Place` | MISSED | no |

**No prompt addition recovered the class, and the nested-Place reading survived every
one.** A zero-shot model that has already committed to the inner span does not release it
because a new label joined the list. (One incidental effect: `"group of people"` alone
made `Ashcombe household` an Organization at sentence level, and adding all three removed
it again — prompt additions perturb the other types too, which is a second reason not to
buy recall this way.)

So the fix is the structure the model cannot see, applied as a rule, anchored on the
model's own output.

---

## 3. The fix — one general rule

`storyweave/nlp/orgs.py`. A span is proposed as an Organization when it is **one to three
capitalised modifier tokens** (a possessive like `Cassian's` counts) immediately followed
by an English **collective noun**. The capitalised modifier is what separates a named body
from a generic one: `the Salt Quarter watch` is promoted, `the watch` is not.

Three properties that make it a rule rather than a hack:

* it **never invents a name** that is not literally in the text;
* it only **adds** spans — a span the model already emitted at any type is skipped, so the
  floor's output is a strict subset of what is persisted, and no mention is ever retyped;
* its mentions carry `extraction_method = 'rule'`, never `gliner`, so a rule-derived
  mention can never be mistaken for a model prediction. Its score field is 1.0, which is
  **not** a confidence and is documented as such.

Knobs are data: `[extraction] promote_group_nouns` and `[extraction] group_nouns` in
`storyweave.toml`. The shipped run used the defaults; no per-work override exists for this
book.

### Where `GROUP_NOUNS` came from

English **collective / organisational** nouns — words denoting a body of people rather
than a place or a thing — assembled from general English vocabulary and from this
project's own ontology documentation (SPEC §5.1 describes Organization as "factions,
houses, orders, governments"). **`docs/ONTOLOGY.md` does not exist in this repository**,
as already recorded in R4 §3; SPEC §5.1 is the ontology of record.

It was written by scanning general English, **not** by reading the corpus and **not** by
reading the annotation. The evidence that it was not fitted to this book, measured: of
its **67** entries, **52 never occur anywhere in the corpus** — only 15 appear at all. A
list fitted to the answer key would not carry 78% dead weight.

### Two false positives the rule produced, and the general fixes for them

Both were found by running the rule on all 40 chapters and reading every node it created
— not by consulting the gold file. Both fixes are general English facts, not a list of the
specific words that went wrong:

| iteration | false positives | general fix |
| --- | --- | --- |
| 1 | `'A ring'` (from "A ring of smugglers"), `'A chancery'`, `'The chancery'` | sentence-initial **determiners** are not proper modifiers |
| 2 | `'And House'`, `'If House'` | sentence-initial **conjunctions** are not either — so the guard became the whole **closed class of English function words** (articles, determiners, pronouns, conjunctions, prepositions, auxiliaries), because a proper modifier is an OPEN-class word |
| 3 (shipped) | **none** | — |

A regression test pins each, including that `Theodore Guild` must still be promoted — the
guard matches whole words, so "The" must not block "Theodore".

---

## 4. What it created, over all 40 chapters — every one, for human judgement

**9 rule-derived mentions → 3 new Organization nodes. 0 false positives.**

New Organization nodes (R3: 22 → R4b: 25; **none lost**):

| new node | judgement |
| --- | --- |
| `Salt Quarter watch` | a city watch — a body of people. Correct. |
| `Cassian's guard` | a named personal guard. Correct. |
| `Vell family` | a noble house. Correct. |

The other 6 promotions reinforced organizations that already existed, which is the rule
agreeing with the model rather than adding to it: `Ninth House` ×3, `Regency Council`,
`Regent's household`, `Ashen Court`.

### Entity scores, 4-type key — [MEASURED]

| | before (R3) | after (R4b) |
| --- | ---: | ---: |
| strict TP / FP / FN | 24 / 17 / 14 | **25 / 17 / 13** |
| strict P / R / F1 | 0.5854 / 0.6316 / **0.6076** | 0.5952 / 0.6579 / **0.6250** |
| Organization TP / FP / FN | 2 / 1 / 5 | **3 / 1 / 4** |
| Organization F1 | 0.400 | **0.545** |
| alias over-merges, all 3 chapters | **0** | **0** |
| under-merges | 2 | 2 |

**False positives did not rise** (17 → 17) while true positives rose, so the gain is not
bought with precision. **Over-merges stay 0**, as required.

---

## 5. The honest part: 6 relations recovered, 0 relations gained

R4's relex + validator were re-run on the new entities with **identical settings** — same
cue lists, same thresholds, same kin guard, same pre-registered configuration from R4.
Nothing was re-tuned.

The relation build is **bit-identical** to R4's: `306 proposals -> 64 edges
(+61 reinforcements), 181 rejected`, same per-relation counts, same rejection counts.
**The three new Organization nodes produced no new edges at all.**

### Recall accounting, before and after

| stage | R4 | R4b | change |
| --- | ---: | ---: | :--- |
| `NOT_IN_THE_TWELVE` | 28 | 28 | — |
| `NO_PROPOSAL` | 12 | **18** | **+6** |
| `ENTITY_MISSING` | 6 | **0** | **−6, eliminated** |
| `WRONG_TYPE` | 2 | 2 | — |
| `VALIDATOR_REJECTED` | 1 | 1 | — |
| `GRADE_INFERRED` | 1 | 1 | — |
| `FOUND` | 1 | 1 | — |

The six relations moved from "we do not have the entity" to "we have the entity and the
model still says nothing about it". Relation micro-F1 is **0.0000** before and after.

### Why the bottleneck moved instead of clearing

**GLiNER-RelEx does its own NER internally.** `RelexExtractor.extract` passes the chunk
text and its own `ENTITY_LABELS` to the model, which re-finds entities from scratch and
then relates the spans it found. It is not given the graph's entity list. So it hits
**exactly the same nested-span preference** that caused the original miss: it sees
`Salt Quarter` (a location) and never proposes a relation whose endpoint is
`Salt Quarter watch`. The grounding step then has no proposal to ground.

Fixing the entity layer therefore cannot, on its own, reach the relation layer. The two
stages re-run the same flawed step independently.

**This is a concrete, testable next step and it is cheaper than it looks:** relex's
internal NER is the wrong place to discover entities when the graph already knows them.
Feeding the known entity spans into relation extraction — or applying the same head-noun
promotion to relex's spans before grounding — is the change that would convert these six.
R4b does not do it, because the brief scoped this phase to Organization recall and doing
it here would be the fourth redesign in one phase.

---

## 6. Controls and gates

| control | result |
| --- | --- |
| gold annotation | never opened during diagnosis, prompt probe, or rule design |
| gold entity names | **no entity is named anywhere in the rule, the vocabulary, or the config** |
| over-merges | **0**, before and after |
| Organization nodes lost | **0** |
| rule-derived false positives, final | **0** of 9 promotions |
| relex settings | unchanged from R4's pre-registration |
| frozen DB | never opened for writing |
| Hollow Crown | unchanged; its tests pass untouched |
| gates | ruff **All checks passed!** · mypy **Success: no issues found in 69 source files** · pytest **266 passed, 6 skipped** (253 → 266, 13 new) |

---

## 7. Viva defense

R4b is the phase that refused the cheap win. The brief's warning was that fixing
`ENTITY_MISSING` would tempt a rule shaped around one gold entity, so the diagnosis was
run against the corpus with the annotation closed, and the measurement that decided the
design was a negative one: four label-prompt additions were tried first and none recovered
the class, which is what justified a rule instead of a prompt. The rule is a general
English construction — capitalised modifier plus collective noun — and the two false
positives it produced were fixed by widening a guard to the whole closed class of function
words rather than by blacklisting the two words that broke. The result is honest in both
directions: the entity layer genuinely improved (Organization F1 0.400 → 0.545, over-merges
still 0, no new false positives) and the relation score did not move one thousandth,
because relex re-runs its own NER and reproduces the identical nested-span error one stage
later. That diagnosis — the two stages independently repeating the same mistake — is worth
more than the point of F1 that narrowing the rule would have bought.
