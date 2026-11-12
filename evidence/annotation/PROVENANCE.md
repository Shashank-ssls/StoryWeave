# Provenance of the reference annotation

This file records how `ch09.json`, `ch17.json` and `ch37.json` were produced. It exists
so that no score derived from them can be read as something it is not.

## How the annotation was produced

- **Model-generated.** The annotations were emitted by **GPT-5**, not written by a human
  annotator.
- **One fresh session per chapter, single run each.** There was no multi-pass
  self-review, no ensembling, and no second model. Each chapter was annotated once.
- **Human verification, partial.** Paragraph indices, alias positions and evidence spans
  were subsequently checked against the source text and **corrected by hand**. The
  *content* judgements — which strings are entities, what type they are, which relations
  hold — were not independently re-derived by a human.
- **ch09 reindexing.** `ch09.json` was emitted 0-indexed and was reindexed to match the
  1-indexed paragraph numbering of `ch09_text.txt`.

## What this means for the scores

- Scores computed against these files measure **agreement between two systems** —
  StoryWeave v1 and GPT-5 — on the same chapters.
- They are **not** accuracy against human ground truth, and they are not to be described
  that way.
- The unqualified phrase "ground truth" is not used for these files anywhere in this
  evaluation.
- Every score is reported **per chapter** as well as aggregated, because with three
  chapters from one work and a single reference source, an aggregate can hide a
  chapter-sized disagreement.

## Scope

| item | value |
| --- | --- |
| work | `the-ninth-house` |
| chapters | 9, 17, 37 |
| chapter lengths | 7, 7 and 9 paragraphs respectively |
| reference source | GPT-5, one session per chapter, single run |
| human involvement | verification and correction of paragraph indices, alias positions and evidence spans; reindexing of ch09 |
| schema | `storyweave-v1-annotation-1`, described in `GUIDELINES.md` (generated from v1's own code and database) |

## Do not modify

These three files are the fixed reference for phase 2. `tools/eval_score.py` opens them
read-only and never writes to them. Validation failures found in them are **logged and
excluded from scoring, not repaired** — repairing the reference in order to score better
against it would make the result meaningless.
