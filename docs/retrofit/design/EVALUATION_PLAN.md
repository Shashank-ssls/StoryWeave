> **v2 design document. The retrofit (tag `retrofit-v1.0`) implemented a subset. See [`docs/retrofit/design/IMPLEMENTED.md`](IMPLEMENTED.md).**

# StoryWeave v2 — Evaluation Plan

**Status:** Phase 0 specification. Frozen before any v2 code is written.
**Companion to:** `ONTOLOGY.md`
**Purpose:** define every metric, its ground truth, its method and its reporting
format *before* the system exists.

---

## 0. Why this is written first

If metrics are chosen after the system is built, the choice is unconsciously
biased toward metrics the system happens to do well on. Fixing them in advance
removes that freedom.

It is also the direct answer to the criticism that features were not decided
before the project commenced.

### 0.1 Reporting rules

These apply to every number this project ever publishes.

1. **Every value is labelled `[MEASURED]` or `[NOT MEASURED]`.** There is no
   third category. A projected, estimated or plausible-looking number is a
   fabrication regardless of intent.
2. **A zero is reported with its tested surface.** "0 leaks across N queries
   covering endpoints X, Y, Z at chapters 1–40" — never "the fence is safe". A
   correct outcome whose failure mode was never stressed is a *weak zero* and is
   labelled as one.
3. **Sample size travels with the score.** A per-type F1 is reported next to its
   instance count. A type with 2 instances must never read as if it had 200.
4. **Errors are reported alongside scores.** Every metric emits its false
   positives and false negatives. The error analysis is the more useful artifact.
5. **No interpretation beyond what the numbers support.** The report does not
   claim the system is good or bad.

### 0.2 What this project is not

StoryWeave is a **zero-shot extraction pipeline**. GLiNER is used pretrained,
as-is. The LLM is used pretrained, as-is. There is no training phase anywhere.

Therefore:

| Metric | Applicable? |
|---|---|
| Loss curve | **No.** No gradient descent, no loss to plot. |
| Accuracy-over-epochs curve | **No.** No epochs. |
| Train/validation split | **No.** Nothing is trained. |
| AUC | **Yes, once** — salience ranking treated as a binary "in principal cast" classifier (§5) |
| Precision / Recall / F1 | **Yes** — the core metrics (§3, §4) |

This is stated plainly in every report. A reader expecting a trained-classifier
evaluation needs to know why this one looks different.

---

## 1. Ground truth

### 1.1 Corpus

| Work | Role | Chapters annotated |
|---|---|---|
| *The Ninth House* | Primary | 3 |
| *Shadow Slave* | Universality guard | 1 |

Four annotated chapters total.

### 1.2 Chapter selection

Chapters are chosen from the data, not by preference:

- **One early** — introduces several entities cleanly
- **One middle** — dense with established relations
- **One late** — contains a death and/or an identity reveal if any exist
- **One Shadow Slave chapter** — from the 1–40 window, chosen for register
  contrast

The selection and its reasoning are recorded in
`evidence/annotation/SELECTION.md`.

### 1.3 Annotation method

Hand-annotated by the author, following `ONTOLOGY.md` as the guideline document.

**The annotation is a validation pass on the ontology, not only an input to
scoring.** Gaps found while annotating are folded into `ONTOLOGY.md` and the
affected chapters re-annotated. Once scoring begins, the guidelines are frozen.

### 1.4 Consistency check

Single-annotator ground truth carries an obvious objection: the same person
wrote the rules, the answers, and the system.

Partial mitigation: a second annotation pass produced independently by a
**different model family** (GPT-5.x or Gemini — never Claude, which built the
system under test), given only the chapter text and the guidelines, in fresh
sessions, **3 runs per chapter**, majority vote across runs.

**Reporting language is mandatory and non-negotiable:**

> This is a **consistency check on guideline clarity**. It is **not** equivalent
> to a second human annotator and must not be reported as inter-annotator
> reliability in the conventional sense.

Two numbers are reported:

| Comparison | Meaning |
|---|---|
| Model run 1 vs 2 vs 3 | Self-stability. Low stability indicates ambiguous guidelines. |
| Author vs model majority | The agreement figure |

Measured with **Cohen's kappa** for categorical layers, **pairwise F1** for
clustering.

| Kappa | Reading |
|---|---|
| > 0.80 | Strong |
| 0.60–0.80 | Substantial — normal for literary annotation |
| 0.40–0.60 | Moderate — guidelines are ambiguous somewhere |
| < 0.40 | Poor — task definition is wrong |

Published literary annotation commonly lands in 0.60–0.80. A result in that band
is reported as expected, not apologised for.

### 1.5 Disagreements are the primary output

Every disagreement is manually reviewed and categorised:

| Category | Action |
|---|---|
| Author error | Correct the annotation, log it |
| Model error | Note, keep the author's |
| **Guideline gap** | **Fix `ONTOLOGY.md`, re-annotate** |
| **Text genuinely ambiguous** | **Document — this is a finding** |

The last category is the most valuable. A statement that a fact is unresolvable
from the source text is a property of the domain, not a limitation of the system.

---

## 2. Metric summary

| # | Layer | Metric | Ground truth |
|---|---|---|---|
| 1 | Entity detection | P / R / F1, overall and per type | Annotation |
| 2 | Significance gate | P / R / F1 on "earns a node" | Annotation |
| 3 | Alias clustering | Pairwise P / R / F1, per label kind | Annotation |
| 4 | Coreference | CoNLL F1 (MUC, B³, CEAFe) | Annotation |
| 5 | Relations | Per-type F1 + macro + micro | Annotation |
| 6 | `KIN_OF` metaphor guard | Precision on kinship specifically | Annotation |
| 7 | `SAME_AS` | **Counts, not F1** | Annotation |
| 8 | Death detection | P / R / F1 | Annotation |
| 9 | Killer attribution | P / R / F1, **separate from 8** | Annotation |
| 10 | Events, per kind | Per-kind F1 + counts | Annotation |
| 11 | Evidence grading | STATED vs INFERRED agreement | Annotation |
| 12 | Salience ranking | P@10, P@20, MAP, **AUC** | Cast list |
| 13 | Spoiler fence | **Leak rate**, not F1 | Exhaustive |
| 14 | Graph readability | Density, degree, counts | Computed |
| 15 | ONNX parity | Agreement rate vs torch | Computed |
| 16 | Performance | Time, RAM, disk | Measured |
| 17 | Universality | All of 1–12, re-run on Shadow Slave | Annotation |

---

## 3. Extraction metrics

### 3.1 Entity detection

Match on `(normalised surface string, type)`. The matching rule is stated
verbatim in the output — a scoring script that does not declare its match rule is
not reproducible.

Reported: overall P/R/F1, plus per type (Character / Organization / Place / Item)
with instance counts.

### 3.2 The significance gate

This is the change v2 exists to make, so it is scored on its own.

Binary task: for each entity in the annotation, should it earn a graph node?

- **Precision** — of the nodes v2 draws, how many should be drawn
- **Recall** — of the nodes that should be drawn, how many are
- Reported separately for the standard path (§3.1 of `ONTOLOGY.md`) and the
  unnamed-but-important path (§3.2)

**Expected direction:** v1 had near-total recall and poor precision. v2 trades
recall for precision. Both numbers are reported; the trade is the result.

### 3.3 Alias clustering

Pairwise: for every pair of mentions, did the system and the annotation place
them in the same cluster?

Reported **per label kind**, because the failure modes differ completely:

| Kind | Expected difficulty |
|---|---|
| `full` / `short` (abbreviation merge) | Moderate — rule-based, §5.3 |
| `title` | Harder — chapter-gated linking |
| `description` | Hardest — no lexical overlap |

Over-merges and under-merges are counted **separately**. They are not
symmetrically bad: a false merge destroys a distinction the reader can see; a
false split only adds a node.

### 3.4 Coreference

MUC, B³, CEAFe, and **CoNLL F1** (the mean of the three — the standard headline).

Reported with the context that v2 deliberately does not depend on coreference for
its default output (`ONTOLOGY.md` §13.1). A weak number here is a stated design
tolerance, not an undiscovered flaw.

Published book-length coreference is an open problem; BookNLP-fr reports around
0.77 mean F. This project will not beat that and does not claim to.

---

## 4. Relation metrics

### 4.1 Per type

Match on `(head, tail, relation)`. Reported per relation type with counts, plus
**macro-F1** (unweighted mean across types) and **micro-F1** (instance-weighted).

Both are reported because they answer different questions. Macro treats a
2-instance type as equal to a 200-instance one; micro does not.

**Expected spread**, stated in advance so the result can be checked against the
prediction:

| Band | Relations | Why |
|---|---|---|
| High | `KIN_OF`, `MEMBER_OF`, `LEADS` | Explicit language |
| Medium | `SERVES`, `LOCATED_IN`, `OWNS` | Often implied by action |
| Medium-low | `ALLY_OF`, `ENEMY_OF`, `ROMANTIC_WITH`, `MENTOR_OF` | Shown through behaviour, rarely declared |
| Low recall, high precision | `KILLED`, `SAME_AS` | Rare, but stated plainly when they occur |

Writing this table before measuring is itself a test. A large deviation from the
prediction is worth investigating.

### 4.2 The `KIN_OF` metaphor guard

Scored separately, because it guards against a specific, common failure.

The annotation marks every kinship word in the text as **literal** or
**metaphorical** (*"such a wonderful little sister"* said to an unrelated person).

Reported:

- Precision on `KIN_OF` edges — how many asserted kinships are real
- **Metaphor rejection rate** — of the metaphorical kinship words present, how
  many did the guard correctly refuse
- False rejections — literal kinships the guard wrongly blocked

Target: metaphor rejection near-total, at an acceptable cost in recall.

### 4.3 `SAME_AS` — counts, never F1

A 40-chapter novel contains perhaps 2–8 identity reveals. At that sample size a
single miss swings F1 by ~0.15, so an F1 is statistically meaningless and its
apparent precision is misleading.

**Reported as counts, in prose:**

> *The Ninth House contains N identity reveals by manual count. The system
> recovered M (all correct, 0 false positives). The unrecovered reveals were
> confirmed across paragraph boundaries, which the sentence-scoped extractor
> cannot span.*

That paragraph is worth more than a number. It states the count, the outcome, and
the mechanism of failure.

**Required outcome: precision = 1.0.** A false identity link is a spoiler or a
false plot claim. Recall may be low and is reported without apology. This metric
is excluded from macro-F1.

### 4.4 Death and killer attribution — two metrics

Detecting *that* someone died is substantially easier than detecting *who did
it*. Merging them hides that.

| Metric | Task |
|---|---|
| Death detection | P/R/F1 on death events |
| Killer attribution | P/R/F1 on `KILLED` edges |
| Cascade correctness | Did death close the right edges, and only those? |
| **Death fence** | Is `death_revealed_ch` used, never `died_chapter`? |

The death fence is a **dedicated test case**, not an aggregate. Construct a
character who dies at chapter N and is revealed dead at chapter N+k, then assert
that a reader between N and N+k sees them alive. This is the single most likely
spoiler leak in the schema.

### 4.5 Evidence grading

For each extracted claim, did the system assign the same grade as the annotation?

Reported as a 2×2 confusion matrix. The dangerous cell is **INFERRED annotated,
STATED assigned** — the system claiming quote-level proof it does not have. That
cell is reported separately with every instance listed.

---

## 5. Events

### 5.1 Per kind

Events are the primary reading surface in v2, so per-kind F1 is a headline
metric, not an appendix.

Reported per kind with counts. **Expected spread**, stated in advance:

| Band | Kinds |
|---|---|
| Good | `death`, `movement`, `gain` |
| Medium | `conflict`, `pact`, `transformation` |
| Medium-low | `reveal` |
| Low | `betrayal`, `discovery`, `loss` |

### 5.2 The shipping rule

**Measured per-kind F1 decides what ships.** A kind scoring below threshold is
excluded from the default timeline and reported as a measured negative result.

This is a designed outcome, not a failure. "We attempted ten event kinds;
measured F1 supports seven; `betrayal`, `discovery` and `loss` are excluded and
reported" is a stronger result than shipping all ten and claiming they work.

The threshold is set **before** the scores are seen, and recorded here:

```
Event kinds ship at F1 >= 0.60 with n >= 5 instances.
Kinds below either bar are excluded and reported.
```

### 5.3 Timeline salience

Whether the "major beats only" filter selects the events a reader would consider
major. Ground truth: a manual list of the major beats per annotated chapter.
Reported as P@k.

---

## 6. Salience ranking

### 6.1 Ground truth

Three people independently list the 20 main characters of *The Ninth House*.

**Inter-annotator agreement between those three is reported** (Krippendorff's
alpha). If humans agree only 0.70 with each other, then 0.70 is the realistic
ceiling, and saying so out loud is a strong result rather than a weak one.

If three people cannot be recruited, the ground truth is the author's list alone
and the sample size is stated plainly as n=1.

### 6.2 Metrics

| Metric | Question |
|---|---|
| P@10, P@20 | Did the right characters make the cut |
| **Recall@20** | Of the real main cast, how many were included |
| MAP | Overall ranking quality |
| **AUC** | "In principal cast" as a binary class, scored by salience |

### 6.3 Ablation

Each feature (§14.1 of `ONTOLOGY.md`) is removed in turn and the metrics
recomputed. This shows which features earn their place and justifies the
equal-weight choice with evidence rather than assertion.

The recency feature is ablated separately, since it only matters at length.

### 6.4 Weight tuning — and its honest caveat

Weights are hand-tuned **once** against the annotation, then written into
`ONTOLOGY.md` §14.2 and frozen.

**Stated limitation:** tuning on the same four chapters used for scoring means
salience numbers are partly in-sample. With a corpus this size, holding out data
is not viable. This is recorded in Threats to Validity rather than hidden.

---

## 7. The spoiler fence

Not an F1. A safety property, measured like one.

### 7.1 Leak rate

```
For each work:
  For each chapter n in 1..max_chapter:
    For each fence surface (six of them, ONTOLOGY.md §11.1):
      Request the payload as a client would
      Assert: no element carries revealed_chapter > n
```

Reported as: **X leaks across N queries inspecting M elements, covering
[explicit list of surfaces], chapters 1..max.**

Target: 0.

### 7.2 Proving the zero is not vacuous

A leak rate of zero means nothing if the detector never fires. Three required
negative tests:

1. **Injection** — insert a synthetic element with `revealed_chapter = n+1` into
   a copy of the database; assert the checker catches it
2. **Death inversion** — construct the N / N+k death case (§4.4); assert the
   reader sees the character alive in between
3. **Label leak** — construct a title linked at chapter N+k; assert a reader
   before N+k cannot see the link

A zero reported without these is a weak zero and is labelled as such.

### 7.3 Surface coverage

All six surfaces are listed with a pass/fail each. Any surface not tested is
listed as **not measured**, never silently omitted.

---

## 8. Graph readability

### 8.1 Metrics

Computed at chapters 10, 20, 30, 40, for each configuration.

| Metric | Formula |
|---|---|
| Nodes (N) | count visible |
| Edges (E) | count visible |
| Mean degree | 2E / N |
| Median degree | median per-node degree |
| **Max degree** | busiest node's edge count |
| Edge density | 2E / (N(N−1)) |
| Isolated nodes | degree 0 |
| Degree-1 nodes | degree exactly 1 |

Median and max are reported because mean degree is distorted by hubs.

### 8.2 Configurations

| Label | Filters |
|---|---|
| `v1_api_payload` | Fence only — frozen baseline |
| `v1_rendered_view` | Fence + v1's client-side filters |
| `v2_fence_only` | Fence only |
| `v2_full` | Fence + salience + backbone + STATED |

Comparing `v1_api_payload` against `v2_full` is the headline. Comparing
`v2_fence_only` against `v2_full` isolates how much work the new filters do.

### 8.3 Growth curves

Plot each metric against chapter, one line per configuration. A **flat line next
to a rising line** demonstrates that v2 does not degrade with length — a stronger
claim than a single-point comparison.

### 8.4 The mandatory caveat

Stated before anyone asks:

> v2's reduction is **by construction** — the salience and backbone filters are
> designed to reduce counts, so a reduction is expected rather than surprising.
> The measurement demonstrates the *magnitude* of the reduction and that it does
> not degrade at scale. It does not demonstrate that reduction occurs.

The interesting question is not whether the graph got smaller but **whether the
right things survived** — which is §6, not §8.

### 8.5 Optional: comprehension pilot

If 3 participants can be recruited: one task per person ("who is X allied
with?"), measured on time-to-answer and correctness, v1 versus v2.

Reported as a **pilot, n=3**, with the small sample stated. If participants
cannot be recruited, this is omitted and §8.1–8.3 carry the argument.

---

## 9. Engineering metrics

### 9.1 ONNX parity

Agreement rate between the torch GLiNER and the ONNX int8 export on identical
input. Expected ~100%. Any divergence is listed case by case.

Same pattern used in the Sentinel project's frozen-model export.

### 9.2 Performance

| Metric | Reported with |
|---|---|
| Extraction time per chapter | CPU, RAM, GPU, OS |
| Peak RSS | |
| Model size on disk | Per model, torch vs ONNX int8 |
| Database size | |
| API response time | Median over 10 calls, per endpoint |

---

## 10. Universality

All metrics in §3–§6 re-run on the *Shadow Slave* annotated chapter.

**The gap between the two works is the finding.** A system that performs well on
its development corpus and poorly on a contrasting one has overfit to a register.
Reported as a side-by-side table.

### 10.1 Stage 0 effectiveness

Measured separately, since it exists because of the *Shadow Slave* source:

| Metric | Method |
|---|---|
| Watermark removal rate | Known contaminants planted, then counted |
| Homoglyph folding | Unicode audit of the cleaned text |
| False removal | Did the cleaner delete legitimate text |
| Quote-mark preservation | Are `" "`, `' '` and `[ ]` still distinguishable |

The last row matters most — collapsing `'` into `"` would corrupt the
speech/monologue distinction that salience depends on.

### 10.2 Scope statement

Required in every report:

> Validated on 40-chapter windows of two serials. Full-length processing of
> long-running serials (1000+ chapters) is not attempted and is future work.

---

## 11. Threats to validity

Stated in every report, unprompted.

| Threat | Statement |
|---|---|
| Single annotator | Ground truth by one person; model-based consistency check is not equivalent to a second human annotator |
| Sample size | Four chapters, two works |
| Per-type sparsity | Several relation and event types have too few instances for a stable F1; counts are reported alongside |
| In-sample tuning | Salience weights tuned on the same chapters used for scoring |
| Corpus scope | 40-chapter windows only |
| Self-designed ontology | The system is scored against a schema the author defined; a different ontology would produce different numbers |
| Fence surface coverage | The leak rate covers the enumerated surfaces only; an unenumerated surface is untested |

---

## 12. Report structure

`evidence/EVAL_V2.md`:

```
 1. System description         zero-shot, no training, why no loss curves
 2. Measurement conditions     commit, branch, DB, machine, date
 3. Ground truth               corpus, selection, method, consistency check
 4. Entity + significance gate [MEASURED]
 5. Alias clustering           [MEASURED]
 6. Coreference                [MEASURED]
 7. Relations                  [MEASURED] per type + macro/micro
 8. SAME_AS                    [MEASURED] counts, in prose
 9. Death + killer attribution [MEASURED]
10. Events per kind            [MEASURED] + which kinds ship
11. Salience + AUC + ablation  [MEASURED]
12. Spoiler fence              [MEASURED] leak rate + negative tests
13. Graph readability          [MEASURED] + growth curves
14. Universality               [MEASURED] side by side
15. Engineering                [MEASURED]
16. Error analysis             categorised, with real examples
17. Threats to validity
18. Future work                the v3 list from ONTOLOGY.md §19
```

Every header carries `[MEASURED]` or `[NOT MEASURED]`.

---

## 13. What is decided by measurement

Three values are deliberately left open in `ONTOLOGY.md` and are set here, by
result rather than argument:

| Value | Set by |
|---|---|
| Salience feature weights | §6.4 hand-tuning, then frozen into `ONTOLOGY.md` §14.2 |
| Which event kinds ship | §5.2, threshold F1 ≥ 0.60 with n ≥ 5, fixed in advance |
| Disparity filter alpha | §8.2 — chosen as the value giving a readable graph at chapter 40 without dropping any top-20 entity, recorded with the reasoning |

Each is recorded with the evidence that set it.

---

*End of plan. Any change to `ONTOLOGY.md` that alters extraction behaviour
requires re-annotation and a corresponding change here.*
