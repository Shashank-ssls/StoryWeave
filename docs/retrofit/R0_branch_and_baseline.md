# R0 — Branch, rules, baseline snapshot

**Goal:** a clean starting point with v1 numbers re-confirmed on the exact commit
the retrofit starts from. No behaviour changes.

## Paste into Claude Code
```
Read CLAUDE.md, SPEC.md, evidence/EVAL_V1.md and docs/retrofit/R0_branch_and_baseline.md.
We are starting the RETROFIT track, phase R0. Do exactly the tasks in R0, then stop.
```

## Tasks
1. `git fetch --all`. Create branch `retrofit/v2-core` from
   `origin/integration/demo-scale` (it contains all of `main` plus the eval
   harness and evidence). Push it.
2. Verify `docs/retrofit/` contains README.md, INIT_PROMPT.md,
   CLAUDE_RETROFIT.md and R0–R8 (the user placed them by hand; they are
   untracked). Commit them on the new branch. Paste the `CLAUDE_RETROFIT.md` block at the TOP
   of `CLAUDE.md`, above the old redesign banner. Mark the old "five
   non-negotiable rules" section with one line: "Superseded by the retrofit
   rules above where they conflict (rules 2 and 3)." Do not delete it.
3. Create `docs/retrofit/RETROFIT_PROGRESS.md` with a table: phase, status,
   commit, key measured numbers, date.
3b. **Local environment lock-down (do this before anything that installs or runs models):**
   - Extend `dev.ps1` and `dev.bat` (session-only, never system/user env vars) to
     also set: `HF_HOME=<repo>\.hf-cache` explicitly, `npm_config_cache`,
     `OLLAMA_MODELS`, `TEMP`, `TMP` — values from the table in CLAUDE.md.
     Create the `.local\...` folders if missing. Keep them gitignored.
   - Create `tools/check_local_env.py` (stdlib only). It exits non-zero if any of
     these resolve to a path not on the repo's drive: `sys.prefix` (must be
     `.venv` or `.venv-ml` inside the repo), `PIP_CACHE_DIR`, `HF_HOME`,
     `TORCH_HOME`, `npm_config_cache`, `PLAYWRIGHT_BROWSERS_PATH`,
     `OLLAMA_MODELS`, `TEMP`, `TMP`, and `pip config list` `user`/`global`
     entries. It prints a table of variable → path → OK/FAIL. With
     `--c-drive-report` it also prints the sizes of the C: cache folders listed
     in task 7 (read-only, never deletes anything).
   - Ollama check (report only, do not install anything): print
     `where ollama` and whether `OLLAMA_MODELS` is set. If Ollama's models
     already exist under `C:\Users\<you>\.ollama\models`, report their size and
     tell the user how to move them; do not move them yourself.
   - Add a test that runs `check_local_env.py` logic against fake paths.
4. Verify the frozen DB: SHA-256 of `evidence/v1_ninth_house.db` matches the
   value recorded in `evidence/BASELINE.md`. If it does not, STOP and report.
5. Re-run the existing harness against the frozen DB (read-only) and confirm
   these v1 figures reproduce: ch40 nodes 206 / edges 1316 served; fence 0
   violations; relation micro-F1 0.046; entity F1 0.532. Write the rerun to
   `evidence/retrofit/R0_baseline_rerun.md` labelled [MEASURED] with commit hash.
6. Add `evidence/retrofit/edge_composition_v1.csv`: counts of edges by
   `extraction_method` × `relation` in the frozen DB.

7. Record the C: baseline so later phases can prove nothing grew: write the
   sizes of `C:\Users\<you>\.cache`, `C:\Users\<you>\AppData\Local\pip`,
   `C:\Users\<you>\.ollama` and `C:\Users\<you>\AppData\Local\ms-playwright`
   (0 if absent) plus the `check_local_env.py` table to
   `evidence/retrofit/R0_local_paths.md`. `tools/check_local_env.py --c-drive-report`
   prints these sizes; later phases compare against this file.

## Do not
- Change any code under `storyweave/` or `frontend/`.
- Write to the frozen DB.

## Acceptance
- [ ] Branch exists and is pushed
- [ ] CLAUDE.md starts with the retrofit block
- [ ] `python tools/check_local_env.py` passes in both venvs (paste the table)
- [ ] Frozen DB hash matches
- [ ] Baseline rerun matches the four v1 figures (any mismatch explained)
- [ ] pytest / ruff / mypy unchanged from baseline
- [ ] `R0_local_paths.md` written with the C: size baseline
- [ ] Commit `chore(retrofit): R0 branch, rules, baseline rerun` + push
