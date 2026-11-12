# R5 — Recall pass: closed-vocabulary LLM proposals (optional enhancement)

**Goal:** lift relation recall without losing precision. The LLM only proposes;
the R4 validator decides. With Ollama off, R4 output stands unchanged.

## Paste into Claude Code
```
Read CLAUDE.md and docs/retrofit/R5_llm_recall_pass.md. Phase R5. R4 is complete.
```

## Preflight (every session in this phase)
`.\dev.ps1 -Ml` then `python tools/check_local_env.py` must pass before any
model load, download or pipeline run. If a model or package is missing, it is
downloaded only inside the repo (see CLAUDE.md table). Fail → stop and report.
Ollama specifics: the Ollama server must be started from the same session
AFTER `OLLAMA_MODELS` is set (`ollama serve` in that shell), otherwise it reads
models from `C:\Users\<you>\.ollama`. Check with `ollama list` and confirm
the model files exist under `.local\ollama_models`. If Ollama itself is not
installed, STOP and tell the user; do not install it. If the models are
missing from `.local\ollama_models`, ask the user before pulling (several GB).

## Tasks
1. Candidate sentences: sentences containing labels of ≥2 principal-ish
   entities (any two stored Character/Org entities) AND a relation cue word
   from the R4 cue lists. Log candidate count per chapter.
2. `storyweave/extract/llm_relations.py` (HTTP via stdlib `urllib`, no new package): send candidate sentence + 2 sentences
   of context to local Ollama (`qwen2.5:7b`, fallback `llama3.2:3b`, config in
   `storyweave.toml`). JSON-only output: list of {relation, head, tail, quote}.
   Relation must be one of the 12 or the model returns []. Temperature 0.
   Parse defensively; malformed JSON → logged, discarded.
3. Every proposal goes through `validator.py` unchanged. No bypass flag.
4. Cache LLM responses keyed by (model, prompt hash) in `.local\llm_cache` so
   reruns are free and reproducible.
5. Budget: if a full 40-chapter run exceeds 45 minutes on the GTX 1650, cap
   candidates per chapter (config) and record the cap.
6. Output `ninth_house_r5.db`.

## Acceptance
- [ ] `tools/check_local_env.py --c-drive-report` passes and C: sizes match the R0 baseline (paste both)
- [ ] Runs end-to-end with Ollama OFF (no crash, zero LLM edges, logged)
- [ ] Relation P/R/F1 R4 vs R5 side by side, per type with counts, in
      `evidence/retrofit/R5_RESULT.md` [MEASURED]
- [ ] If R5 precision drops below R4 precision by > 0.10, disable the pass by
      default and report it as a measured negative result — do not tune on the
      answer key to rescue it
- [ ] Green gates, commit `feat(retrofit): R5 LLM recall pass`, push
