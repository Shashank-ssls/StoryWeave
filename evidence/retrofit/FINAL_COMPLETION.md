# Final repo completion (2026-11-12)

## 1. What is on GitHub

- `main` = `83785a0`, a `--no-ff` merge of `retrofit/v2-core` (no conflicts). This file is committed on top.
- `retrofit/v2-core` = `9abdccf` at merge time, pushed normally.
- Tag `retrofit-v1.0-final` -> `9abdccf` (the old `retrofit-v1.0` -> `0366e4e` was left in place).
- Safety tag `pre-retrofit-main` -> `291b89a`, the previous `main`.

## 2. Removed and kept

The repo was already close to clean; the audit found no tracked venvs, caches, build output,
weights, secrets or files over 5 MB.

| category | removed | size |
| --- | --- | --- |
| redundant `.gitkeep` in non-empty folders | 4 (`data/labels`, `data/samples`, `eval`, `frontend`) | 0 B |

`.gitignore` gained: model weights, `.env.*` (keeping `.env.example`), OS/editor files, `*.tmp`,
`_incoming/`. `git ls-files -ci --exclude-standard` returns nothing, and the frozen artifacts are
still tracked. `*.log` was deliberately not ignored: the tracked logs are cited evidence.

Kept, please review:
- `docker/.gitkeep`: an empty folder named in `SPEC.md` and `SETUP_NOTES.md`.
- `logs/`: R7/R8 run logs at top level; `EVAL_RETROFIT.md` cites them by path, so they were not moved.
- `tools/build_r5_db.py`, `tools/build_r6_db.py`, `tools/r5_antecedent_diagnostic.py`: no references,
  but they rebuild the evaluated database. They are now named in the README.
- `docs/design/StoryWeave Redesign Directions.pdf` (3.1 MB), referenced by `DESIGN_SPEC.md`.
- Undeclared imports: `playwright`, `PIL`, `numpy` (in `tools/`). Not added: the run rule says no dependency changes.
- `SPEC.md`, `PROGRESS.md`, `SETUP_NOTES.md` still describe the original 8-type/Tier-1 design.
  They are dated records of the original build and were not rewritten.

Not applicable: `_incoming/` did not exist. Process docs were already in `docs/retrofit/`.
`PREDICTIONS.md`, listed as frozen in CLAUDE.md, does not exist anywhere in this repo's history.

## 3. README

Rewritten from scratch with sections 1 to 11 of the brief. Number sources:
- fence, payload, timing: `logs/R8_eval_fence.log`, `logs/R8_compare.log`
- relation and entity F1, false positives: `logs/R8_score_final_v1key.log`, `logs/R8_score_final_proj.log`
- salience AUC: `evidence/retrofit/logs/R6_salience_score.log` (via `EVAL_RETROFIT.md` §3.3)
- predictions 6 / 12 / 1: `evidence/retrofit/PROJECTION_CHECK.md`

**Fence recount [MEASURED]:** the per-kind rows in `logs/R8_eval_fence.log` (200 + 4092 + 4860 +
4860 + 3951 + 4860 + 379 + 555 + 1052 + 4020 + 40) sum to **28,869**, equal to the logged total,
with 0 violations over 12,660 queries. 28,046 is the R6 run (`evidence/retrofit/logs/R6_eval_fence.log`),
before R7 widened the cast dial. Both figures are correct for their own runs; the README uses 28,869.

Images: one screenshot, `evidence/retrofit/shots/R7/desktop_ch40_default.png`, opened and checked
before linking. It predates the later arrowhead fix (`3b046b4`). All relative links resolve.
`storyweave seed-demo --no-ninth-house --db <path>` was run and printed
`seeded 'the-hollow-crown' (work id=1) into ...`.

## 4. Gates (verbatim)

| gate | before (Phase 0) | after cleanup | on merged main |
| --- | --- | --- | --- |
| pytest | `318 passed, 6 skipped in 182.05s (0:03:02)` | `318 passed, 6 skipped in 182.77s (0:03:02)` | `318 passed, 6 skipped in 183.83s (0:03:03)` |
| ruff | `All checks passed!` | same | same |
| mypy | `Success: no issues found in 112 source files` | same | same |
| npm run build | `✓ built in 3.28s`, exit 0 | exit 0 | exit 0 |
| frozen DB SHA-256 | `C7264C16…D946FF` (matches R0) | same | n/a |

Playwright (`npx playwright test --workers=1`, API serving `storyweave-demo.sqlite`):
`1 failed`, `1 skipped`, `100 passed (2.7m)`. The failure was
`reveal-choreography.spec.ts:37` (`thread.scaleX` 0.0168, floor 0.02), a timing assertion. Rerun
3 times with `fence.spec.ts`: `33 passed` each time. An earlier attempt against a Hollow-Crown-only
DB failed the F6 arcs test, because that test needs the 40-chapter work; that was a setup error.

C: drive (`check_local_env.py --c-drive-report`): `.cache` 180.5 MB and `.ollama` 2.2 KB, unchanged
during this run. They do **not** equal R0 (`.cache` 135.8 MB): the difference is `chrome-devtools-mcp`
(an MCP tool's cache, not StoryWeave) and predates this run. `AppData\Local\Temp` is OS-shared and
includes the assistant session's own temp folder.

## 5. Unverified, assumed, not done

- `gh` is not installed, so the GitHub description and topics were not set, and nothing beyond
  `git ls-remote` was checked on GitHub.
- The README's Windows quick start was checked against `dev.ps1`, the CLI help and the Vite proxy,
  but not run from a fresh clone.
- Playwright was not re-run on merged `main`; its tree is identical to `retrofit/v2-core` (empty diff).

## 6. Rollback (no reset, no force-push)

```
git checkout main
git revert -m 1 83785a0      # undo the merge, keeping history
git push origin main
```
The previous `main` stays reachable as tag `pre-retrofit-main`.
