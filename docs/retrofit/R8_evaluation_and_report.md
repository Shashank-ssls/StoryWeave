# R8 — Evaluation, evidence report, replace projections with measurements

**Goal:** one report an examiner can check, with every projection from the
professor doc replaced by a measured value (or shown to be wrong).

## Paste into Claude Code
```
Read CLAUDE.md, EVALUATION_PLAN.md, PREDICTIONS.md and docs/retrofit/R8_evaluation_and_report.md.
Phase R8. R7 is complete.
```

## Preflight (every session in this phase)
`.\dev.ps1 -Ml` then `python tools/check_local_env.py` must pass before any
model load, download or pipeline run. If a model or package is missing, it is
downloaded only inside the repo (see CLAUDE.md table). Fail → stop and report.

## Tasks
1. Final pipeline run on The Ninth House 40 chapters → `data/retrofit/ninth_house_final.db`.
   Record commit, machine (GTX 1650, CPU, RAM, OS), date, models + versions.
2. Run all metrics on the final DB:
   - Fence leak rate across all R6 surfaces × chapters 1–40, + negative controls
     + the label-reveal constructed test
   - Relation P/R/F1 micro + macro, per type with counts; SAME_AS as counts
   - **Like-for-like:** relation F1 of the final system scored on the ORIGINAL
     v1 answer key and match rule (map 12 relations back where a 1:1 mapping
     exists; list unmappable ones). This is the only valid "before vs after" F1.
   - Entity + significance gate + alias metrics (4-type key; no delta vs v1)
   - Salience AUC, P@10, P@20, MAP, Recall@20
   - Readability at ch 10/20/30/40 for: v1_api_payload, v1_rendered_view,
     retrofit_fence_only (cast=all, all types), retrofit_default
     (cast=20, Characters). Nodes, edges, mean/median/max degree, density,
     isolated, degree-1. Growth-curve PNGs (matplotlib only if already in a venv; otherwise add it to `.venv-ml` requirements + lock).
   - Performance: extraction time/chapter, peak RSS, DB size, `/graph` and ego
     median over 10 calls
   - Universality spot check on Shadow Slave ch 1–40 if the text is present:
     density + fence only (no annotation → no F1; say so)
3. `evidence/retrofit/EVAL_RETROFIT.md`, section headers each `[MEASURED]` or
   `[NOT MEASURED]`: system description (zero-shot, why no loss curves) ·
   conditions · results · error analysis with real examples (validator
   rejections by reason, top false negatives by cause) · threats to validity ·
   future work.
4. `evidence/retrofit/PROJECTION_CHECK.md`: table of every [PROJECTED] value from
   the professor doc and every [PREDICTED] band from PREDICTIONS.md vs the
   measured value, with "inside / outside band" and one line on why. Do not
   edit the predictions.
5. Update README: what StoryWeave does in 3 sentences, screenshots, the
   headline measured numbers, how to run the demo tier.

## Acceptance
- [ ] `tools/check_local_env.py --c-drive-report` passes and C: sizes match the R0 baseline (paste both)
- [ ] Every number in EVAL_RETROFIT.md traceable to a script + log in `evidence/logs/`
- [ ] Fence: 0 violations with surface list, or the leak is fixed before writing
- [ ] PROJECTION_CHECK.md complete, nothing omitted
- [ ] Green gates, commit `docs(retrofit): R8 evaluation`, push, tag `retrofit-v1.0`
- [ ] Phase summary to me: the 8 headline numbers, one line each
