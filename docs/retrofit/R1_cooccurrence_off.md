# R1 — Switch off co-occurrence edges and re-score (the one-hour experiment)

**Goal:** turn the headline projection into a measurement. Same answer key as v1,
so this comparison is fully like-for-like.

## Paste into Claude Code
```
Read CLAUDE.md and docs/retrofit/R1_cooccurrence_off.md. Phase R1. R0 is complete.
```

## Tasks
1. In `storyweave/ingest/work_config.py` `RelationConfig`, add
   `cooccurrence_enabled: bool = False`. In `storyweave/graph/builder.py`,
   `build_relationships` returns an empty report (and does not clear other
   edges' tiers) when it is false. Keep the code path; it is evidence.
2. Make `repo.clear_edges` in the builder scoped to `extraction_method='rule'`
   only, so disabling/enabling the rule never deletes relex or identity edges.
   Add a test for this.
3. Build a derived DB `evidence/retrofit/r1_rule_off.db`: copy of the frozen DB
   with every `extraction_method='rule'` edge removed. (Do not re-extract.)
4. Re-score it with the existing scorer against `evidence/annotation/ch09/17/37`
   using the exact same match rule and both scope variants (chapter_local,
   cumulative). Report TP/FP/FN, P/R/F1 micro and macro, per relation with counts.
5. Recompute density metrics at ch 10/20/30/40 for r1_rule_off (nodes, edges,
   mean/median/max degree, isolated nodes).
6. Write `evidence/retrofit/R1_RESULT.md`, every figure [MEASURED], with a
   side-by-side against v1. State plainly if the 5 true positives were lost
   (they may have come from the rule). State isolated-node count — expect a
   large number; that is the recall problem R4/R5 address.

## Do not
- Touch the annotation or the scorer's match rule.

## Acceptance
- [ ] Unit test: config flag off → zero rule edges created
- [ ] Unit test: rule rebuild does not delete gliner/llm edges
- [ ] R1_RESULT.md with v1 vs rule-off table, both scopes
- [ ] Green gates, commit `feat(retrofit): R1 co-occurrence off by default + rescore`, push
- [ ] Report the measured micro-F1 to me in the phase summary
