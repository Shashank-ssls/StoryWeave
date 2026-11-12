# R0 — baseline rerun against the frozen v1 database

**Purpose.** Re-confirm the v1 numbers on the exact commit the retrofit starts from, so
every later phase has a like-for-like starting point measured on *this* machine, in *this*
checkout, rather than one carried over from the evaluation session.

| field | value |
| --- | --- |
| date | 2026-09-28 |
| branch | `retrofit/v2-core` |
| branch point / commit measured | `0202df1049ebada97b8d7ba237d7b87e9ba34eb5` (`origin/integration/demo-scale`) |
| database | `evidence/v1_ninth_house.db`, opened `mode=ro` |
| work measured | `the-ninth-house` (`work_id = 2`), 40 chapters |
| venv | `.venv` (Python 3.14) via `dev.ps1` |
| LLM | off (`llm_enabled = False`); no model loaded, no outbound call |

Runner logs, verbatim: `evidence/retrofit/logs/R0_eval_fence.log`,
`R0_eval_score.log`, `R0_graph_metrics.log`, `R0_check_local_env_venv.log`,
`R0_check_local_env_venv_ml.log`.

No code under `storyweave/` or `frontend/` was changed in R0. The frozen DB was not
written (see §5).

---

## 1. Frozen database integrity — [MEASURED]

```
c7264c16dbd9223bbdb0eeceb4699e0243ba8a93130b544d351fdfe5fdd946ff *evidence/v1_ninth_house.db
```

| check | recorded in `evidence/BASELINE.md` | measured now | verdict |
| --- | --- | --- | --- |
| SHA-256 | `C7264C16DBD9223BBDB0EECEB4699E0243BA8A93130B544D351FDFE5FDD946FF` | `c7264c16…d946ff` | **match** (case only) |
| size | 847,872 bytes | 847,872 bytes | match |
| file mode | read-only | `-r--r--r--` | match |

---

## 2. The four v1 figures — [MEASURED]

| figure | v1 value (`evidence/EVAL_V1.md`) | R0 rerun | verdict |
| --- | --- | --- | --- |
| ch40 nodes served | 206 | **206** | reproduces |
| ch40 edges served | 1316 | **1316** | reproduces |
| fence violations | 0 / 105,243 elements | **0 / 105,243 elements** | reproduces |
| relation micro-F1 (pooled, `chapter_local`) | 0.046 | **0.0459** | reproduces |
| entity F1 (pooled, strict) | 0.532 | **0.5319** | reproduces |

All five reproduce with no unexplained difference. Detail follows.

### 2.1 Graph size at every measured chapter

`tools/graph_metrics.py --config api_payload`, verbatim:

```
api_payload | api_payload | the-ninth-house | 10      | 90    | 503   | 498            | 5
api_payload | api_payload | the-ninth-house | 20      | 138   | 774   | 767            | 7
api_payload | api_payload | the-ninth-house | 30      | 167   | 970   | 961            | 9
api_payload | api_payload | the-ninth-house | 40      | 206   | 1316  | 1307           | 9
```

(columns: label | config | slug | chapter | nodes | edges | distinct_pairs | parallel_edges)

Cross-checked against the real endpoint, `GET /api/v1/works/the-ninth-house/graph?n=N`
served in-process through FastAPI's `TestClient` with
`STORYWEAVE_DB_PATH=evidence/v1_ninth_house.db`:

```
n=10: served nodes=90  served edges=503
n=20: served nodes=138 served edges=774
n=30: served nodes=167 served edges=970
n=40: served nodes=206 served edges=1316
```

The harness and the endpoint agree exactly at all four chapters.

### 2.2 Fence

`tools/eval_fence.py`, verbatim from `logs/R0_eval_fence.log`:

```
total queries issued:    8424
total elements inspected: 105243
    arc_name: 200
    detail_edge: 59764
    detail_entity: 5210
    detail_property: 7
    entity: 5210
    graph_edge: 29635
    graph_node: 5210
    graph_node_property: 7
TOTAL VIOLATIONS: 0
```

**The zero is reported with its tested surface** (rule 9): 0 violations over 105,243
reveal-stamped elements drawn from 8,424 queries across seven element classes, on both
works in the DB (`the-hollow-crown` chapters 1..4, `the-ninth-house` chapters 1..40).

The detector was proved to fire, on throwaway copies, not the frozen DB:

```
  injected: 3 synthetic elements revealed at chapter 6, payload fetched at 6, checked against n=5
    queries=4 elements=362 violations_detected=123
  sabotaged: fenced reads replaced with unfenced ones, payload fetched at n=5 as a client would
    queries=43 elements=2694 violations_detected=3556

DETECTOR VERIFIED TO FIRE: True
```

### 2.3 Agreement scores

`tools/eval_score.py`, verbatim from `logs/R0_eval_score.log`:

```
--- pooled over chapters 9, 17, 37 ---
  [strict] TP=25 FP=23 FN=21  P=0.5208 R=0.5435 F1=0.5319
  [alias_aware] TP=27 FP=21 FN=19  P=0.5625 R=0.5870 F1=0.5745
```

```
--- pooled [chapter_local] --- TP=5 FP=162 FN=46
  micro P=0.0299 R=0.0980 F1=0.0459   macro-F1 over 15 relation types: 0.0087
      tier 1: TP=5 FP=160 FN=39 F1=0.048
      tier 2: TP=0 FP=1 FN=7 F1=0.000
      tier 3: TP=0 FP=1 FN=0 F1=0.000
```

```
--- pooled [cumulative] --- TP=9 FP=229 FN=42
  micro P=0.0378 R=0.1765 F1=0.0623   macro-F1 over 17 relation types: 0.0099
```

Alias clustering, pooled: `TP=3 FP=0 FN=3  P=1.0000 R=0.5000 F1=0.6667` — **0
over-merges**, 3 under-merges. No SAME_AS-family false positive. Neither stop condition
is tripped.

**The retrofit's central claim is confirmed at the source:** of 162 pooled relation false
positives, **160 are Tier-1** — the co-occurrence rule — which is what R1 switches off.

> These are **agreement** figures against a model-generated (GPT-5) reference annotation
> with hand-verified indices, not accuracy against human ground truth. See
> `evidence/annotation/PROVENANCE.md`. Stated here so the number is never read as more
> than it is.

---

## 3. Edge counts: the three numbers, and defect D1 — [MEASURED]

These are three different quantities and are reported separately.

| # | quantity | value |
| ---: | --- | ---: |
| 1 | total edge rows in the DB for `work_id = 2` | **1326** |
| 2 | rows passing the fence at ch40 (`revealed_chapter <= 40`, SQL) | **1326** |
| 3 | edges served by `GET /…/graph?n=40` | **1316** |

Every edge in the work is revealed by chapter 40, so (1) and (2) coincide — the fence
drops nothing at the last chapter. **The 10-edge gap between (2) and (3) is entirely the
projection layer: defect D1.**

`graph/serialize.py:build_graph` projects into `nx.DiGraph`, which cannot hold parallel
edges, so a second row on the same *ordered* pair silently overwrites the first. 1326
fenced rows sit on 1316 distinct ordered pairs; 9 pairs are doubled and one is tripled,
losing 10 rows. **D1 reproduces exactly as `evidence/EVAL_V1.md` §7 recorded it. It is
not fixed in R0 — R4 fixes it.**

The loss happens *after* `query/fence.py` has returned its rows, so it is outside the
fence's control and cannot leak: a collapse can only ever show fewer elements than the
reader is entitled to, never more.

All ten lost rows, enumerated:

| ordered pair | row lost | row that overwrote it |
| --- | --- | --- |
| 14 → 150 | id 772 `RelatedTo` (t1, rule) | id 1327 `REINCARNATION` (t3, curated) |
| 14 → 150 | id 1325 `SECRET_IDENTITY` (t3, curated) | id 1327 `REINCARNATION` (t3, curated) |
| 30 → 32 | id 79 `RelatedTo` (t1, rule) | id 1329 `Sibling` (t2, curated) |
| 30 → 147 | id 894 `RelatedTo` (t1, rule) | id 1326 `REINCARNATION` (t3, curated) |
| 31 → 78 | id 355 `RelatedTo` (t1, rule) | id 1330 `Parent` (t2, curated) |
| 31 → 99 | id 500 `RelatedTo` (t1, rule) | id 1331 `Parent` (t2, curated) |
| 45 → 99 | id 503 `RelatedTo` (t1, rule) | id 1323 `SECRET_IDENTITY` (t3, curated) |
| 47 → 60 | id 203 `RelatedTo` (t1, rule) | id 1322 `ALIAS` (t3, curated) |
| 62 → 69 | id 253 `RelatedTo` (t1, rule) | id 1333 `Mentor` (t2, curated) |
| 69 → 213 | id 1233 `RelatedTo` (t1, rule) | id 1328 `TRANSMIGRATED_INTO` (t3, curated) |

**Defect D2 is the second row of that table and reproduces exactly:** on pair 14 → 150
the curated `SECRET_IDENTITY` edge (id 1325) is overwritten by `REINCARNATION` (id 1327),
which is why `SECRET_IDENTITY` counts read 1, 2, 2, 1 across chapters 10/20/30/40 instead
of rising. Under rule 1 — the graph models revealed reader-knowledge — a reveal whose
*type* changes in the projection layer is the more serious of the two defects.

Two observations for R4, both [MEASURED]:

- 9 of the 10 lost rows are `RelatedTo` co-occurrence edges, which R1 removes anyway. The
  *only* substantive loss in this database is the one identity edge, D2.
- Every collision is a curated Tier-2/Tier-3 edge landing on a pair the co-occurrence rule
  had already claimed. A multigraph (or a per-pair relation list) fixes both defects at once.

Node counts have no equivalent gap: 206 rows, 206 revealed at ch40, 206 served.

---

## 4. Edge composition — [MEASURED]

Full table in `evidence/retrofit/edge_composition_v1.csv`
(`extraction_method` × `relation`, all 1326 rows of `work_id = 2`).

| extraction_method | edges |
| --- | ---: |
| `rule` (Tier 1, co-occurrence) | 1307 |
| `curated` (Tier 2 + Tier 3, from the story bible) | 19 |
| `llm` | **0** |
| `gliner` | 0 |

Matching `EVAL_V1.md` §1 exactly (1307 / 12 + 7 / 0). The `rule` half breaks down as
`RelatedTo` 565, `LocatedIn` 347, `OwnsItem` 115, `ParticipatedIn` 113, `LeaderOf` 58,
`MemberOf` 58, `HasTitle` 26, `HasAbility` 17, `AffiliatedWith` 8 — i.e. **98.6% of all
edges in the shipped v1 graph come from the co-occurrence rule R1 disables**, and 43% of
those are the never-drop `RelatedTo` fallback.

---

## 5. One harness bug found and fixed — [MEASURED]

`tools/eval_fence.py` could not run against the frozen DB at all:

```
sqlite3.OperationalError: attempt to write a readonly database
  File "tools/eval_fence.py", line 450, in negative_injected
```

Cause: `_copy_db` uses `shutil.copy2`, which preserves mode bits, so the throwaway copy
of the deliberately read-only baseline DB was itself read-only and the negative control
could not inject its canary. Fix: `chmod` the *copy* (in `TEMP`, now on F:) to writable.
Two lines plus a comment; the source database is still never opened for writing. The
measurement run above (§2.2) is unaffected by the fix — it had already completed and
printed `TOTAL VIOLATIONS: 0` before the crash, and its numbers are identical after.

This is the first time any harness ran against the frozen copy rather than the live
`storyweave-demo.sqlite`, which is why it had not surfaced before.

---

## 6. Gates — [MEASURED]

| gate | baseline (this commit, before R0) | after R0 |
| --- | --- | --- |
| `pytest` (`.venv`) | `152 passed, 6 skipped` | `167 passed, 6 skipped` (+15 new `test_check_local_env.py`) |
| `ruff check .` | **`Found 20 errors.`** | `All checks passed!` |
| `mypy` | `Success: no issues found in 78 source files` | `Success: no issues found in 78 source files` |

The pre-existing tests are unchanged: re-running the suite with the new test file moved
aside gives `152 passed, 6 skipped` — the same as the baseline.

**Ruff was not clean at the baseline** and CI (`.github/workflows/ci.yml` runs
`ruff check .`) was therefore red on `integration/demo-scale`. All 20 findings were
cosmetic and confined to `tools/` — 17 `E501` over-long lines, 2 unsorted import blocks,
1 `f`-string with no placeholder — so they were fixed in R0 by wrapping lines and sorting
imports. No behaviour changed: the only non-mechanical edit lifted a long conditional in
`run_evidence.py` into a named `counts_agree` variable with the same truthiness, and the
metrics it feeds were re-derived identically in §2.1. `storyweave/` and `frontend/` were
not touched.

`pytest` is not installed in `.venv-ml`; the suite is a `.venv` gate by design (heavy
imports are lazy and guarded with `importorskip`, which is where the 6 skips come from).

---

## 7. Stop conditions — none tripped [MEASURED]

| stop condition | status |
| --- | --- |
| `tools/check_local_env.py` fails | PASS in both venvs, 10/10 checks (§`R0_local_paths.md`) |
| any fence violation | 0 / 105,243 elements, detector verified to fire |
| any alias over-merge | 0 over-merges (3 under-merges) |
| any SAME_AS false positive | 0 |
| ch40 default graph < 10 or > 40 nodes | not applicable yet — v1 has no default-cast filter; ch40 serves 206 nodes, which is the problem R6/R7 fix |
| R5 lowering precision by > 0.10 | not applicable (R5 not run) |
