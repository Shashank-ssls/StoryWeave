# StoryWeave retrofit — phase prompts

Upgrade v1 in place with the v2 fixes the measurements blame. Nine phases,
strictly sequential, commit + push at each boundary.

| Phase | What | Main output | Needs ML/GPU |
|---|---|---|---|
| R0 | Branch, rules, baseline rerun | CLAUDE.md retrofit block, baseline confirmed | no |
| R1 | Co-occurrence off + rescore on v1 key | First measured like-for-like F1 | no |
| R2 | Stage 0 cleaner | No watermark or homoglyph junk | no |
| R3 | 4 node types + entity_labels | Type confusion removed | yes (GLiNER) |
| R4 | 12 relations + validator + weight | Every edge quoted; D1/D2 fixed | yes (relex) |
| R5 | LLM recall pass (optional) | More STATED edges | yes (Ollama) |
| R6 | Salience per chapter + 4-clause query + ego API | Cast dial works; D3 fixed | no |
| R7 | Frontend readability, timeline removed | ~20 labelled people, click for quotes | no |
| R8 | Evaluation + projection check | EVAL_RETROFIT.md | yes (final run) |

## How to use
1. Put this folder in the repo as `docs/retrofit/` by hand (do not commit).
   Open a fresh Claude Code session and paste the prompt in `INIT_PROMPT.md`.
2. One fresh Claude Code session per phase (Sonnet, high effort). Paste only
   the "Paste into Claude Code" block; the file carries the rest.
3. Do not start a phase until the previous acceptance checklist is all ticked
   and pushed.
4. Bring each phase summary back to the planning chat before starting the next.

## If time runs out
Minimum viable path for a demo: R0 → R1 → R4 → R6 → R7. R2, R3, R5 improve
accuracy; skipping them is a documented scope cut, not a failure. R1 alone
already gives you one real measured number to show.

## Stop conditions (tell me immediately)
`tools/check_local_env.py` fails · Any fence violation · any alias over-merge · any SAME_AS false positive ·
ch40 default graph < 10 or > 40 nodes · R5 lowering precision by > 0.10.
