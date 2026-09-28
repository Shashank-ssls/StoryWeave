# Retrofit progress — branch `retrofit/v2-core`

The v2 fixes applied inside v1. Rules: `docs/retrofit/CLAUDE_RETROFIT.md` (also pasted at
the top of `CLAUDE.md`). Phase prompts: `docs/retrofit/R0_*.md` … `R8_*.md`. Every number
below is labelled **[MEASURED]**, **[PREDICTED]** or **[PROJECTED]**.

Start of every session: read this file, state the current phase, do that one phase, stop.
No phase starts until the previous one is green, committed and pushed.

## Status

| phase | what | status | commit | key measured numbers | date |
| --- | --- | --- | --- | --- | --- |
| R0 | branch, rules, baseline rerun | **green** | `fe16415` | [MEASURED] frozen-DB SHA-256 match · ch40 206 nodes / 1316 edges served · fence 0 violations / 105,243 elements · relation micro-F1 0.0459 · entity F1 0.5319 · D1 = 1326 fenced rows → 1316 served (10 lost) · 1307 of 1326 edges are `rule` · 160 of 162 relation FPs are Tier-1 · env gate 10/10 in both venvs | 2026-09-28 |
| R1 | co-occurrence off + rescore on the v1 key | not started | — | — | — |
| R2 | Stage 0 cleaner | not started | — | — | — |
| R3 | 4 node types + `entity_labels` | not started | — | — | — |
| R4 | 12 relations + validator + weight (fixes D1/D2) | not started | — | — | — |
| R5 | LLM recall pass (optional) | not started | — | — | — |
| R6 | salience per chapter + 4-clause query + ego API (fixes D3) | not started | — | — | — |
| R7 | frontend readability, timeline removed | not started | — | — | — |
| R8 | evaluation + projection check | not started | — | — | — |

Minimum viable demo path if time runs out: R0 → R1 → R4 → R6 → R7. R2, R3, R5 are
accuracy work; skipping them is a documented scope cut, not a failure.

---

## R0 — branch, rules, baseline snapshot · green, 2026-09-28

Full evidence: `evidence/retrofit/R0_baseline_rerun.md` and
`evidence/retrofit/R0_local_paths.md`. Logs: `evidence/retrofit/logs/R0_*.log`.

### Acceptance

- [x] Branch `retrofit/v2-core` exists, cut from `origin/integration/demo-scale`
      (`0202df1`), and is pushed.
- [x] `CLAUDE.md` starts with the retrofit block; the old five non-negotiable rules are
      marked superseded where they conflict (rules 2 and 3), not deleted.
- [x] `python tools/check_local_env.py` passes in both venvs — 10/10 checks, tables
      pasted in `R0_local_paths.md` §1–2.
- [x] Frozen DB hash matches `evidence/BASELINE.md`
      (`c7264c16…d946ff`, 847,872 bytes, still read-only).
- [x] Baseline rerun reproduces all four v1 figures, no unexplained mismatch:
      206 nodes / 1316 edges served at ch40 · 0 fence violations over 105,243 elements ·
      relation micro-F1 0.0459 · entity F1 0.5319.
- [x] pytest / ruff / mypy: pre-existing tests unchanged (`152 passed, 6 skipped` with the
      new file aside; `167 passed, 6 skipped` with it), mypy unchanged
      (`no issues found in 78 source files`), **ruff improved from `Found 20 errors.` to
      `All checks passed!`** — see the honesty note below.
- [x] `R0_local_paths.md` written with the C: size baseline.
- [x] Commit `chore(retrofit): R0 branch, rules, baseline rerun` + push.

### Numbers established for later phases to beat — all [MEASURED]

| quantity | R0 value |
| --- | ---: |
| edge rows in the DB (`work_id = 2`) | 1326 |
| rows passing the fence at ch40 | 1326 |
| edges served by `/graph?n=40` | 1316 |
| edges from the co-occurrence rule | 1307 (98.6%) |
| of those, `RelatedTo` never-drop fallback | 565 |
| nodes served at ch40 | 206 |
| relation FPs that are Tier-1 | 160 of 162 |
| alias over-merges / SAME_AS false positives | 0 / 0 |
| fence violations | 0 over 105,243 elements |

### D1 and D2 confirmed, not fixed (R4 fixes them)

`nx.DiGraph` cannot hold parallel edges, so 10 of the 1326 fenced rows are overwritten in
the projection layer. Nine are `RelatedTo` co-occurrence edges (which R1 deletes anyway);
the tenth is the real defect, **D2**: on pair 14 → 150 the curated `SECRET_IDENTITY` edge
(id 1325) is overwritten by `REINCARNATION` (id 1327). Every collision is a curated
Tier-2/3 edge landing on a pair the rule builder had already claimed, so a multigraph (or
a per-pair relation list) fixes both at once. Full table of all ten in
`R0_baseline_rerun.md` §3.

### Two things R0 fixed that it had to

1. **`tools/eval_fence.py` could not run against the frozen DB.** `_copy_db` used
   `shutil.copy2`, which preserves mode bits, so the throwaway copy of the read-only
   baseline was itself read-only and the negative control died with
   `sqlite3.OperationalError: attempt to write a readonly database`. The copy is now
   chmod'd writable; the source is still never opened for writing.
2. **`ruff check .` was red at the baseline (20 errors), so CI was red.** All 20 were
   cosmetic and all in `tools/`: 17 over-long lines, 2 unsorted import blocks, 1
   placeholder-less f-string. Fixed by wrapping and sorting. One non-mechanical edit: a
   long ternary in `run_evidence.py` became a named `counts_agree` variable with identical
   truthiness. No behaviour change, and §2.1 of the rerun re-derives the same metrics.
   `storyweave/` and `frontend/` were not touched, per R0's "do not".

### Honesty note

R0's acceptance asks for the gates to be "unchanged from baseline". Two of the three are
exactly unchanged. Ruff is **better** than baseline, not unchanged, and that is stated
rather than glossed: the baseline was 20 errors, which means the claim "the original build
ended green on ruff" was not true of this commit for `tools/`. The 20 findings are listed
above so the change is auditable.

### Viva defense

R0 buys the one thing the retrofit cannot fake: a like-for-like starting point measured in
this checkout, so every later delta is a real delta and not a comparison against numbers
copied out of a previous session's report. It also converts the "nothing on C:" rule from
a habit into an executable gate with 15 tests behind it — the variable that was actually
leaking was `TEMP`, which no cache setting would have caught. The rerun confirms the
retrofit's premise at the source rather than on trust: 1307 of 1326 edges come from the
co-occurrence rule, and 160 of 162 relation false positives are Tier-1, so R1 — switching
one flag off — is aimed at the whole of the measured error, not a slice of it.
