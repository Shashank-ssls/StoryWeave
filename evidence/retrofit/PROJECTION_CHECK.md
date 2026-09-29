# R8 — every pre-registered band against its measured value

One row per band committed **before** the run that measured it. **Nothing pre-registered
has been edited**; where a band was missed it is marked missed and the original band is
reproduced as written. The commit hash in each row is the commit that fixed the band.

Legend: **IN** = measured value inside the band · **OUT** = outside · **n/a** = the band
could not be evaluated, with the reason given.

---

## 0. The withdrawn headline projection

| quantity | projected | measured | verdict |
| --- | --- | ---: | --- |
| relation micro-F1 after removing co-occurrence | **0.20 – 0.35** | **0.0000** | **OUT — withdrawn at R1** |

**A sourcing caveat, stated rather than papered over.** This projection came from the
planning document that framed the retrofit. **That document is not in this repository** —
the same situation `CLAUDE.md` records for `FINDINGS.md` ("never committed and is not a
source here"), and the same one R4 hit with `docs/ONTOLOGY.md`. `PREDICTIONS.md` and
`EVALUATION_PLAN.md`, both named in the R8 phase doc, are likewise absent; `git log --all`
shows no commit ever added them. The band above is therefore reproduced **from the user's
statement of it**, not from a file I can point at, and this row is the only one in this
document whose source is not a committed artifact.

**Why it was withdrawn.** R1 turned the projection into a measurement and the measurement
refuted it. Removing the Tier-1 co-occurrence rule moved relation micro-F1 from **0.0459 to
0.0000** — *worse*, not better — because all five of v1's true positives were co-occurrence
edges. The rule emitted 1,307 edges to catch 5. R1_RESULT.md §1 states it directly: *"the
retrofit's projection that removing co-occurrence raises relation F1 is not supported by
this measurement; what the measurement supports is the precondition for raising it."*

That precondition was real and is the phase's actual result: false positives **162 → 2**,
a 98.8% reduction. Precision's denominator was fixed. The numerator was never filled.

---

## 1. R4 — the twelve closed relations and the validator (`d99e445`, scored at `f1204f0`)

| quantity | pre-registered | measured | verdict |
| --- | --- | ---: | --- |
| STATED micro-F1 on the 12-relation key | 0.05 – 0.20 | **0.0000** | **OUT (low)** |

Why: the validator was not the constraint — it rejected exactly 1 of the 51 reference
relations. Model recall was. R4's stop condition ("if STATED micro-F1 < 0.05, do NOT loosen
the validator") fired and was honoured: nothing was loosened, and the phase was reported as
a negative result.

---

## 2. R4c — relex grounded on known entities (`5d25d3a`, scored at `b5469a2`)

| quantity | pre-registered | measured | verdict |
| --- | --- | ---: | --- |
| ring-1 edges at ch40 | 4 – 25 | **4** | **IN** (at the floor) |
| ring-2 edges at ch40 | 60 – 150 | **64** | **IN** |
| STATED micro-F1 | 0.05 – 0.25 | **0.0000** | **OUT (low)** |

Why the headline missed: `input_spans` was accepted by the library and then **ignored** —
byte-identical output with and without it, in both NER modes — so a span-snapping fallback
was built instead. It grounded 30 spans and recovered zero relations, because the 125
ungrounded endpoints are pronouns and common nouns (`She` ×14). That is coreference, not
recall, and R4c is the phase that proved it.

The two bands that landed inside did so at the bottom of their ranges, which is worth
saying: "inside the band" is not the same as "good".

---

## 3. R5 — the LLM recall pass (`4aedbbb`, scored at `b60902b`)

| quantity | pre-registered | measured | verdict |
| --- | --- | ---: | --- |
| ring-1 edges at ch40, STATED | 5 – 25 | **4** | **OUT (low)** |
| default-view edges at ch40 | 3 – 15 | **1** | **OUT (low)** |
| STATED micro-F1 | 0.05 – 0.30 | **0.0000** | **OUT (low)** |
| STATED precision | 0.50 – 0.90 | **0.0000** | **OUT — stop condition fired** |
| antecedent diagnostic (INFERRED that would be STATED) | 5 – 20 | **2** | **OUT (low)** |

**All five missed.** The stop condition ("if STATED precision < 0.5, stop, no tuning")
fired and was honoured. The antecedent diagnostic was explicitly pre-registered as
*measure but do not ship*, and it was not shipped — the loosening it describes would have
been the easiest way to manufacture a better headline.

R5 is also where the validator first earned its keep: it caught **5 invented relations and
3 paraphrased quotes**, the first non-zero values in that column in the project's history.

**Self-caught contamination.** The KIN_OF few-shot example named Lord Fennick Oswald and
Brenna Oswald — legal under the "chapters outside {9,17,37}" rule, but that pair is a ch17
gold relation. It was flagged, run A was preserved as a sensitivity check, and the phase
was re-run with a different ch2 pair. The comparison showed the example taught the *quote
format*, not the relation.

---

## 4. R6 — salience, the four-clause query, the ego API (`4114cd8`, scored at `c372ac4`)

| quantity | pre-registered | measured | verdict |
| --- | --- | ---: | --- |
| salience AUC | 0.70 – 0.92 | **0.6667** | **OUT (low)** — and defined at only 1 of 3 chapters |
| salience P@10 | 0.55 – 0.85 | **0.8750** | **OUT (high)** |
| default-view dots, ch10 | 8 – 20 | **10** | **IN** |
| default-view dots, ch20 | 15 – 20 | **7** | **OUT (low)** |
| default-view dots, ch40 | 20 | **12** | **OUT (low)** |

Two misses in opposite directions, and neither was rescued.

**The P@10 overshoot is not good news.** It is high because at ch17 and ch37 every matched
reference entity is flagged significant, so there are no negatives and P@k cannot score
below 1.0 whatever the ordering. The band was set for a metric that could discriminate; the
data could not.

**The dots misses were traced and deliberately left in place.** The pre-registered clause
order was *cast rank → node type*, and the stored rank is global across all four types, so
"cast 20" meant the top twenty **entities** and the type clause then removed the
non-Characters — 12 of 20 at ch40. Re-ordering the clauses after seeing a number I disliked
is exactly what pre-registration exists to prevent, so R6 shipped the miss and recommended
the change. **R7 made it, as a user decision, and R6's miss stands unedited** in
`R6_RESULT.md` — the ch40 default view is now 20 of 20.

---

## 5. R7 — the readable graph (`93988e7`)

R7's pre-registration opens with a disclosure that matters more than its rows: **the dots
and lines were already MEASURED** before the section was written, because verifying that
step 0's SQL ran at all meant running the report that prints them. They are recorded as
measured, not dressed up as predictions. Only the rows below were genuinely blind.

| quantity | pre-registered | measured | verdict |
| --- | --- | ---: | --- |
| INFERRED share of lines, ch10 | 70 – 100% | **100%** (3 of 3) | **IN** |
| INFERRED share of lines, ch20 | 70 – 100% | **100%** (7 of 7) | **IN** |
| rendered elements == payload elements | exact equality | **dots: exact. lines: no** | **OUT — criterion mis-specified** |
| edge labels legible at 1280×720, ch40 | ≥ 80% | **4 of 13 (31%)** | **OUT (low)** |
| chapters (of 10/20/40) needing the low-edge note | 0 | **0** | **IN** |

Three rows need their one line:

- **The INFERRED bands were hit, and that is honest rather than good.** 100% means the ch10
  and ch20 default views contain *no stated relationship at all* — every line is dashed.
- **"Rendered == payload" was wrong as written, not failed.** Node counts match exactly in
  every view. Edge counts do not, because §7.3 merges parallel edges into one line per pair
  (18 payload edges draw as 13 lines at ch40). Nothing is dropped, and R7 made the merged
  line name every relation it absorbed. Recorded as a mis-specified criterion rather than
  quietly restated to something it passes.
- **The label band was missed badly.** At 1280×720 the canvas is 652px once the rail and
  panel are subtracted, and twenty names plus thirteen relation labels do not both fit.
  Both orderings were built and screenshotted; names-first shipped (20 of 20 names, 4 of 13
  labels) because relations-first gave "serves (implied)" pointing at anonymous dots. The
  nine deferred labels return on zoom and on focus. R7_RESULT.md §12.1 has the measurements
  and the R8 recommendation.

---

## 6. Tally

| | count |
| --- | ---: |
| bands pre-registered across R4 – R7 | **19** |
| inside | **6** |
| outside | **12** |
| mis-specified (criterion wrong, not failed) | **1** |
| bands edited after seeing the result | **0** |
| stop conditions that fired | **2** (R4, R5) |
| stop conditions honoured | **2** |

**Six of nineteen.** The pattern is not random: the bands that landed inside are counts of
things the system emits (ring-1 edges, ring-2 edges, dots at ch10, INFERRED share), and the
bands that missed are almost all *quality* measures — every F1 band, every precision band.
The system was consistently predicted to be more accurate than it is, by the person who
built it, in writing, before each measurement. That is what the pre-registration was for.
