# StoryWeave v1 — evaluation, phases 1 and 2

Phase 1: metrics that need no reference annotation, measured on the current system.
Phase 2: agreement against a reference annotation of three chapters.

Every number below was produced by code run in the session that measured it and read off
its stdout. Nothing is estimated, projected, interpolated or carried over from a previous
run. Where something could not be measured it says **not measured** and why, in one line.

Section headers carry **[MEASURED]** or **[NOT MEASURED]**.

Runner logs, kept verbatim: `evidence/logs/eval_fence.log`, `eval_salience.log`,
`eval_performance.log`, `make_annotation_template.log`, `eval_score.log`,
`eval_errors.log`.

**Sections 1–7 and 16 are phase 1** — metrics that need no reference annotation.
**Sections 8–15 are phase 2** — agreement against a MODEL-GENERATED reference
annotation (GPT-5) with human-verified indices. Phase-2 figures are not accuracy
against human ground truth; §8 and §15 state exactly what they are.

---

## 1. System description — [MEASURED]

StoryWeave v1 is a **zero-shot extraction pipeline**. **There is no training phase**:
no dataset is fitted, no weights are updated, no epochs are run. **Loss curves,
epoch-accuracy curves, train/validation splits and early-stopping plots are therefore
not applicable to this system** and are not "missing" from this report — they do not
exist for it.

The three stages, and what actually produced the measured data:

| stage | mechanism | provenance tag in the DB |
| --- | --- | ---: |
| entity extraction | zero-shot GLiNER over each chunk, 14 free-text label prompts mapped onto the 8-type ontology (`storyweave/nlp/labels.py`) | `gliner` |
| Tier-1 relations | no ML at all: same-chapter co-occurrence inside a `window_chars` window, relation chosen from a fixed type-pair table with a lexical `MemberOf`→`LeaderOf` promotion, `RelatedTo` as never-drop fallback (`storyweave/graph/builder.py`) | `rule` |
| Tier-2 / Tier-3 relations | **hand-curated from a written story bible.** The LLM layer is off (`llm_enabled = False`); no model produced these, so they are tagged `curated`, never `llm` | `curated` |

Models and their provenance, as loaded in the measured run:

| model | provenance | role |
| --- | --- | --- |
| `urchade/gliner_small-v2.1` | Hugging Face Hub, third-party pre-trained | the extraction floor |
| `microsoft/deberta-v3-small` | Hugging Face Hub, pulled in as GLiNER-small's encoder/tokenizer backbone | dependency of the above |

Both now live in the machine-wide cache at `F:\Dev\shared\hf-cache`, outside the repo
(see §6).

`knowledgator/gliner-relex-base-v1.0` (Tier-2 RelEx) is present in that shared cache but
**was not loaded in this measurement**. `sentence-transformers/all-MiniLM-L6-v2` (search
embeddings) is configured in `storyweave/config.py` and is **not on disk anywhere**.
Neither was exercised, so neither appears in the performance numbers.

Counts in the measured database, `the-ninth-house` (`work_id = 2`), 40 chapters:

- nodes by type: `Place` 55, `Character` 53, `Item` 28, `Event` 22, `Concept` 21,
  `Organization` 16, `Title` 6, `Ability` 5 — 206 total, all `extraction_method = gliner`,
  all with `subtype = NULL`.
- edges: 1307 `rule` (Tier 1), 12 `curated` Tier 2, 7 `curated` Tier 3 — 1326 total.
- 0 edges carry `extraction_method = llm`.

---

## 2. Measurement conditions — [MEASURED]

| item | value |
| --- | --- |
| date | 2026-09-27 (both phases) |
| branch | `integration/demo-scale` |
| commit, phase 1 (§1–§7, §16) | `f22f669b57b085d578e0f73d62c3d4921d1371ae`; the phase-1 tools were uncommitted working-tree files when run and landed in the commit that first added this report |
| commit, phase 2 (§8–§15) | `e928ca5dea485980bc4ff6dae0bef5cd6f465add`; `tools/eval_score.py` and `tools/eval_errors.py` were uncommitted working-tree files when run and land in the commit that adds §8–§15 |
| reference annotation | `evidence/annotation/ch{09,17,37}.json` — MODEL-GENERATED (GPT-5), see §8 and `evidence/annotation/PROVENANCE.md` |
| measured database | `storyweave-demo.sqlite`, 847,872 bytes, SHA-256 `c7264c16dbd9223bbdb0eeceb4699e0243ba8a93130b544d351fdfe5fdd946ff` |
| frozen baseline | `evidence/v1_ninth_house.db`, 847,872 bytes, same SHA-256 — byte-identical to the measured file, opened `mode=ro` where touched |
| OS | `Windows-11-10.0.26200-SP0` (version `10.0.26200`) |
| CPU | `AMD Ryzen 5 4600H with Radeon Graphics` — 6 cores / 12 threads, max 3000 MHz |
| RAM | 16,505,966,592 bytes (15.37 GiB) |
| GPU | `AMD Radeon(TM) Graphics` [0.50 GiB reported, driver 27.20.11028.5001]; `NVIDIA GeForce GTX 1650` [4.00 GiB reported, driver 32.0.15.9636] |
| Python | 3.12.13 (`.venv-ml` for extraction, `.venv` for the rest) |
| torch | `2.12.1+cpu`, `torch.cuda.is_available() == False` |
| extraction device | `cpu` (from `storyweave.config`; the per-work `storyweave.toml` sets no override) |

The GPU is present but **unused**: the installed torch build is CPU-only, so every
extraction number below is a CPU number.

All measurement scripts drive the real `Repository` and the real `query/fence.py`;
none re-implements SQL. Read-only access goes through `tools/swconfig.open_readonly`,
which binds a `mode=ro` URI connection to a real `Repository`.

---

## 3. Spoiler fence leak rate — [MEASURED]

Tool: `tools/eval_fence.py`. Output: `evidence/fence_leaks.csv`.

### Tested surface, stated

Found by reading the router in `storyweave/api/app.py`, not assumed. Requested through
the real FastAPI app as a client would.

**Tested (4 routes, 8 element kinds):**

| route | element kinds checked | rule asserted |
| --- | --- | --- |
| `GET /works/{slug}/entities?n=` | `entity` | `revealed_chapter <= n` |
| `GET /works/{slug}/graph?n=` | `graph_node`, `graph_edge`, `graph_node_property` | `revealed_chapter <= n`; **plus** the both-endpoints rule for every edge; node `properties` carry no reveal stamp on the wire, so each `{key: value}` pair is resolved back to its `node_properties` rows and flagged if no row with `revealed_chapter <= n` could have produced it |
| `GET /works/{slug}/entity/{id}?n=` | `detail_entity`, `detail_edge`, `detail_property` | `revealed_chapter <= n`, requested for **every** node id of the work at **every** chapter, so an unrevealed id must 404 — a 200 on an unrevealed id is itself recorded as a violation |
| `GET /works/{slug}/arcs?n=` | `arc_name` | F6 name redaction: an arc with `start_chapter > n` must send `name: null` |

**Not tested, and why:**

- `GET /works/{slug}/search?n=&q=` — **not measured**: the vector store directory
  (`.chroma`) does not exist in this checkout, so there is no index to query and the
  route cannot be exercised without first building one. Its fence key is chunk
  `chapter_ordinal <= n`.
- `GET /works/{slug}/status` — not a leak surface under this metric: it returns no story
  element, only an **unfenced** `node_count` (`repository.count_nodes` ignores the
  chapter). That is a count, not a reveal-stamped element, so it is out of scope —
  recorded here because it is a real side channel this checker does not cover.
- `GET /works`, `GET /health`, and the write routes (`POST /works`, `POST /works/preview`,
  `POST /works/{slug}/chapters`, `DELETE /works/{slug}`) — no reveal-stamped element in
  the response.

**Chapters covered:** every chapter from 1 to each work's maximum —
`the-hollow-crown` 1..4, `the-ninth-house` 1..40. Both works in the DB, not just one.

### Result

Quoted verbatim from `evidence/logs/eval_fence.log`:

```
=== MEASUREMENT RUN ===
database: F:\Dev\Claude_folder_project_and_stuff\StoryWeave\storyweave-demo.sqlite (opened mode=ro)
  the-hollow-crown: chapters 1..4
  the-ninth-house: chapters 1..40
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

**Leak rate: 0 violations in 105,243 elements inspected across 8,424 queries** on the
surface stated above. This is not a statement that the fence is safe — it is the result
of this checker on these four routes, these eight element kinds, these 44 chapters,
this database.

Two caveats attached to that zero, both visible in the counts:

1. **Property coverage is thin.** Only 7 `detail_property` and 7 `graph_node_property`
   elements were inspected in total, because `the-ninth-house` has **zero**
   `node_properties` rows; all 3 property rows in the database belong to
   `the-hollow-crown`. The property fence is therefore barely exercised by the
   measurement run — it is exercised properly only by the negative controls below.
2. **The search fence is untested**, per the row above.

### Negative controls — the detector was verified to fire

Both run against a **copy** of the database in a temporary directory, deleted afterwards.
The measured database was never written.

**(a) `injected`.** A synthetic node, edge and node-property, all with
`revealed_chapter = 6`, were INSERTed into the copy. The payload was then fetched at
chapter 6 — where the fence correctly serves them, which proves the injected rows really
do reach the serializer — and the checker was run with the bound `n = 5`:

```
  injected: 3 synthetic elements revealed at chapter 6, payload fetched at 6, checked against n=5
    queries=4 elements=362 violations_detected=123
```

The 123 are the three canaries plus every element legitimately first revealed at
chapter 6 (the bound shift flags those too, by construction). What matters is that the
canaries were caught on **every** element kind they appear as:

```
entity              220          revealed 6   entity 'SYNTHETIC LEAK CANARY' revealed at 6 served at n=5
graph_node          220          revealed 6   node 'SYNTHETIC LEAK CANARY' revealed at 6
graph_node_property 220:canary   revealed 6   property canary='synthetic' on node 220 is revealed no earlier than 6
detail_entity       220          revealed 6   entity 'SYNTHETIC LEAK CANARY' served at n=5
detail_edge         1341         revealed 6   edge RelatedTo on entity 220
detail_property     220:canary   revealed 6   property canary='synthetic'
```

**(b) `sabotaged`.** The app was served over a `Repository` subclass whose three fenced
reads (`list_nodes_revealed`, `list_edges_revealed`,
`list_node_properties_revealed`) ignore the chapter argument — a deliberately broken
fence — and the payload was fetched at `n = 5` exactly as a client would:

```
  sabotaged: fenced reads replaced with unfenced ones, payload fetched at n=5 as a client would
    queries=43 elements=2694 violations_detected=3556
      detail_edge: 569
      entity: 158
      graph_edge: 2671
      graph_node: 158
```

```
DETECTOR VERIFIED TO FIRE: True
```

The zero in the measurement run is therefore not vacuous: the same checker, on the same
routes, reports thousands of violations the moment the fence stops filtering.

---

## 4. Graph density — [MEASURED]

Numbers pulled unchanged from the phase-0 harness output
(`evidence/metrics_api_payload.csv`, `metrics_rendered_view.csv`,
`metrics_rendered_everyone.csv`, produced by `tools/graph_metrics.py`). **Nothing was
recomputed here by a different method.** `the-ninth-house`.

`api_payload` — exactly what `GET /works/{slug}/graph` sends (spoiler fence only):

| chapter | nodes | edges | distinct pairs | parallel | mean deg | median deg | max deg | density | isolated | degree-1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 90 | 503 | 498 | 5 | 11.1778 | 9.0 | 57 | 0.124345 | 0 | 0 |
| 20 | 138 | 774 | 767 | 7 | 11.2174 | 8.5 | 83 | 0.081138 | 0 | 1 |
| 30 | 167 | 970 | 961 | 9 | 11.6168 | 8.0 | 96 | 0.069331 | 0 | 2 |
| 40 | 206 | 1316 | 1307 | 9 | 12.7767 | 8.0 | 121 | 0.061899 | 0 | 1 |

`rendered_view` (cast = principal) and `rendered_everyone` (cast = everyone) — the
payload after the frontend's own client-side filters. **The two are identical at every
chapter**, which is measured defect #3 below:

| chapter | nodes | edges | mean deg | median deg | max deg | density | isolated | degree-1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 74 | 369 | 9.973 | 8.0 | 48 | 0.136616 | 0 | 0 |
| 20 | 108 | 569 | 10.537 | 8.0 | 69 | 0.098477 | 0 | 0 |
| 30 | 127 | 709 | 11.1654 | 8.0 | 77 | 0.088614 | 0 | 0 |
| 40 | 157 | 989 | 12.5987 | 8.0 | 99 | 0.080761 | 0 | 0 |

Density falls as the graph grows (0.124 → 0.062 in the payload) while mean degree rises
slightly (11.18 → 12.78): the graph is getting larger faster than it is getting denser,
and no node is ever isolated, because Tier-1's `RelatedTo` fallback never drops a
co-occurring pair.

Per-node-type and per-relation breakdowns for the same runs are in
`evidence/metrics_*_by_node_type.csv` and `evidence/metrics_*_by_relation.csv`.

---

## 5. Salience ranking, structural — [MEASURED]

Tool: `tools/eval_salience.py`. Output: `evidence/salience_v1.csv` (601 rows).
`the-ninth-house`, chapters 10 / 20 / 30 / 40.

There is **no salience ranker in this codebase** — `evidence/BASELINE.md` records that a
search for `salience|disparity` returns zero code hits. What is measured is whether the
two structural signals the schema does carry agree with each other.

- **degree** — incident edges in the payload the API sends at chapter N (so the DiGraph
  collapse of defect #1 is included, exactly as the reader sees it).
- **mention count** — the schema **does** have one: `mentions` rows carry `node_id` and
  `chapter_ordinal`. Counted over mentions with `chapter_ordinal <= N` whose node is
  fenced-visible at N, aggregated in Python over the existing `repository.list_mentions`
  read (no new SQL).

Quoted from `evidence/logs/eval_salience.log`:

```
mentions rows for this work: 887
  of which unclustered (node_id IS NULL, excluded): 103
```

### Agreement between the two rankings

| chapter | fenced-visible entities | Spearman ρ (degree vs mention count) | entities tied on degree within the top 20 | distinct degree values in the top 20 |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 90 | 0.7508 | 11 (in 5 tied groups) | 14 |
| 20 | 138 | 0.7378 | 9 (in 4 tied groups) | 15 |
| 30 | 167 | 0.7347 | 9 (in 4 tied groups) | 15 |
| 40 | 206 | 0.7166 | 8 (in 4 tied groups) | 16 |

ρ is computed over **all** fenced-visible entities at that chapter, on tie-corrected
average ranks (Pearson of the ranks; scipy is not a dependency of either venv, so the
tie handling is written out in `average_ranks`).

The two signals agree substantially but not closely (ρ ≈ 0.72–0.75), and agreement
**decreases** as the graph grows. Degree ties are common in the top 20 — 8 to 11 of
its members share a degree value with another member — so degree alone cannot
produce a stable ordering of the principal cast.

### Top 20 at chapter 40, both rankings

| # | by degree | degree | by mention count | mentions |
| ---: | --- | ---: | --- | ---: |
| 1 | Sorrel (Character) | 121 | Sorrel (Character) | 108 |
| 2 | Cassian (Character) | 68 | Thessaly (Character) | 35 |
| 3 | Meraude (Character) | 64 | Vesper (Character) | 29 |
| 4 | Thessaly (Character) | 62 | Cassian (Character) | 27 |
| 5 | Vesper (Character) | 60 | Corwin (Character) | 23 |
| 6 | Chancery (Organization) | 55 | Undercroft (Place) | 19 |
| 7 | Corwin (Character) | 48 | Meraude (Character) | 18 |
| 8 | Bone Market (Place) | 46 | Chancery (Organization) | 16 |
| 9 | Thorne (Character) | 45 | Hask (Character) | 14 |
| 10 | Undercroft (Place) | 45 | Choir (Organization) | 13 |
| 11 | Council (Organization) | 42 | Thorne (Character) | 13 |
| 12 | ledger (Item) | 37 | Bone Market (Place) | 12 |
| 13 | Regent (Character) | 36 | Juno Stray (Character) | 12 |
| 14 | Hask (Character) | 35 | Ninth House (Place) | 12 |
| 15 | Ione (Character) | 34 | Council (Organization) | 11 |
| 16 | Juno Stray (Character) | 34 | Ione (Character) | 11 |
| 17 | Choir (Organization) | 28 | ledger (Item) | 10 |
| 18 | Warden (Character) | 28 | Denna (Character) | 9 |
| 19 | Denna (Character) | 26 | Drask (Character) | 9 |
| 20 | Master Vane (Character) | 26 | Vey (Character) | 9 |

Chapters 10, 20 and 30 have the same tables in the log and in the CSV. One visible
disagreement worth naming: `Thessaly` is 2nd by mentions and 4th by degree, while
`Meraude` is 3rd by degree and 7th by mentions — the co-occurrence window rewards
entities that appear in crowded scenes, mention count rewards entities named often.
Also note `ledger` (a lowercase common noun) sits in both top 20s.

**Not computed here, deliberately:** P@k, MAP and AUC. They require a reference
annotation of which entities are actually significant. They ARE computed in §13, against the model-generated reference annotation described in §8.

---

## 6. Performance — [MEASURED]

Tool: `tools/eval_performance.py`, run under `.venv-ml`. Output:
`evidence/performance_v1.csv` (46 rows). Machine specs are in §2.

### Extraction — the real pipeline

A scratch database was created in a temporary directory, the first **5 chapters** of the
`the-ninth-house` sample were ingested through `ingest.pipeline.ingest` with the work's
own `storyweave.toml`, and the real extractor was run over them. Quoted verbatim:

```
extraction.gliner_model                 urchade/gliner_small-v2.1   (device=cpu, threshold=0.4; per-work toml overrides: model=None, device=None, threshold=None)
extraction.chapters_measured            5 chapters   (ch01.txt, ch02.txt, ch03.txt, ch04.txt, ch05.txt)
extraction.ingest_total                 0.0964 s   (work 'perf-ninth-house' (id=1): +5 chapters, ~0 updated, =0 unchanged, +21 chunks, 0 cruft lines removed)
extraction.peak_rss_before_model_load   284041216 bytes   (270.9 MiB)
extraction.model_load                   10.3554 s
extraction.peak_rss_after_model_load    1779683328 bytes   (1697.2 MiB)
extraction.extract_chapter:ch01         0.9612 s   (5 chunks, 1710 chars, 31 raw spans)
extraction.extract_chapter:ch02         0.7178 s   (4 chunks, 1718 chars, 30 raw spans)
extraction.extract_chapter:ch03         0.7374 s   (4 chunks, 1504 chars, 33 raw spans)
extraction.extract_chapter:ch04         0.6809 s   (4 chunks, 1499 chars, 22 raw spans)
extraction.extract_chapter:ch05         0.7166 s   (4 chunks, 1436 chars, 23 raw spans)
extraction.extract_chapter_median       0.7178 s   (over 5 chapters)
extraction.extract_chapter_mean         0.7628 s   (over 5 chapters)
extraction.extract_chapter_min          0.6809 s
extraction.extract_chapter_max          0.9612 s
extraction.extract_work_total           4.577 s   (work id=1: 117 mentions -> 47 entities (Ability:3, Character:16, Concept:2, Event:2, Item:10, Organization:3, Place:10, Title:1))
extraction.extract_work_per_chapter     0.9154 s   (extract_work_total / 5 chapters (model already loaded))
extraction.peak_rss_after_extraction    1779683328 bytes   (1697.2 MiB — peak working set of the whole process)
extraction.scratch_db_size              163840 bytes   (5 chapters ingested + extracted (scratch DB, then deleted))
```

**Exactly what was measured:**

- `extract_chapter:chNN` is the GLiNER stage over that chapter's chunks — the same
  `ext.extract(chunk.text)` loop `nlp.pipeline.extract_work` runs — with the model
  already loaded. **This is the per-chapter number: median 0.7178 s, mean 0.7628 s over
  5 chapters, on CPU.**
- `extract_work_total` is one call to the real `extract_work` over the same 5 chapters,
  so it also includes the mention writes and the work-level alias-clustering pass, which
  are not per-chapter costs. Its 0.9154 s/chapter is a whole-pipeline figure, not a
  second estimate of the same thing.
- A full 40-chapter re-run was **not** performed; 5 chapters were measured, and no
  40-chapter total is stated anywhere in this report, extrapolated or otherwise.
- `model_load` was 10.3554 s with a **warm** Hugging Face cache. The first run of this
  session, on a cold cache, measured 75.0108 s including the download — that number is
  a download, not a load time, and is recorded only here. The cache was cold only
  because the config default points at `<repo>/.hf-cache`; see the correction under
  "Model size on disk".

**Peak RSS during extraction: 1,779,683,328 bytes (1697.2 MiB)** — the process's peak
working set (Win32 `GetProcessMemoryInfo` → `PeakWorkingSetSize`, via ctypes; no
third-party dependency). Before loading the model it was 270.9 MiB, so the GLiNER model
plus torch accounts for roughly 1.4 GiB of it. The peak did not rise further during
extraction itself.

### Model size on disk

| model | bytes | location at measurement time |
| --- | ---: | --- |
| `urchade/gliner_small-v2.1` | 610,659,026 | `<repo>/.hf-cache/hub/models--urchade--gliner_small-v2.1` |
| `microsoft/deberta-v3-small` | 2,465,286 | `<repo>/.hf-cache/hub/models--microsoft--deberta-v3-small` |
| **total cache** | **613,124,507** | `<repo>/.hf-cache/hub` |

**Correction, and where the weights actually live now.** `<repo>/.hf-cache` was empty at
the start of this session, so the measured run downloaded these weights into it — that
is what the table above measured. But the repo path was never the right home for them: a
populated machine-wide cache already existed at `F:\Dev\shared\hf-cache` holding the
same two models (plus RelEx), and the run did not use it only because
`storyweave/config.py` defaults `hf_home` to `<repo>/.hf-cache`. The 613 MB download was
therefore redundant. After the measurement the repo cache was moved out and deleted; the
weights now live at:

| model | bytes | location now |
| --- | ---: | --- |
| `urchade/gliner_small-v2.1` | 610,659,026 | `F:\Dev\shared\hf-cache\hub\models--urchade--gliner_small-v2.1` |
| `microsoft/deberta-v3-small` | 2,465,286 | `F:\Dev\shared\hf-cache\hub\models--microsoft--deberta-v3-small` |
| `knowledgator/gliner-relex-base-v1.0` (not loaded) | 911,510,271 | `F:\Dev\shared\hf-cache\hub\models--knowledgator--gliner-relex-base-v1.0` |

The `gliner_small-v2.1` byte count is identical in both locations, and the shared copy
was verified to load and extract with `HF_HUB_OFFLINE=1`, so the measured sizes stand
and no re-download is needed. `.hf-cache/` is in `.gitignore:59`; no model weight was
ever committed (verified against the full history). `sentence-transformers/all-MiniLM-L6-v2`
is not on disk in either location.

### Database size

| file | bytes |
| --- | ---: |
| `storyweave-demo.sqlite` (measured) | 847,872 |
| `evidence/v1_ninth_house.db` (frozen baseline) | 847,872 |
| `data/storyweave.sqlite` (empty, 0 works) | 122,880 |
| scratch DB, 5 chapters ingested + extracted | 163,840 |

### API response time — median of 10 calls per endpoint per chapter

Against the real FastAPI app over a read-only connection to `storyweave-demo.sqlite`,
`the-ninth-house`, in-process (`TestClient`), one untimed warm-up call before each set.
These are **server-side handler times; no network hop and no browser rendering**.

| endpoint | n=10 | n=20 | n=30 | n=40 |
| --- | ---: | ---: | ---: | ---: |
| `/entities` | 5.227 ms | 6.333 ms | 5.954 ms | 6.514 ms |
| `/graph` | 12.816 ms | 18.061 ms | 25.050 ms | 25.803 ms |
| `/arcs` | 4.284 ms | 4.461 ms | 4.467 ms | 4.118 ms |

`/graph` roughly doubles between chapter 10 and chapter 40 as the payload grows from
90/503 to 206/1316 nodes/edges. `/arcs` is flat (5 arcs at every chapter). The single
93.563 ms `/graph` maximum at n=40 is one outlier sample within a set whose median is
25.803 ms; the min/max of every set is in `evidence/performance_v1.csv`.

`GET /works/{slug}/entity/{id}` and `GET /works/{slug}/search` were **not** timed:
the former is not a per-chapter endpoint (it is per entity), and the latter has no
vector index in this checkout, as in §3.

---

## 7. Measured defects — [MEASURED]

Restated from `evidence/BASELINE.md`, where they were measured; not re-derived here.

**1. Parallel-edge collapse.** `graph/serialize.py:build_graph` projects into an
`nx.DiGraph`, which cannot hold parallel edges, so a second edge on the same **ordered**
pair overwrites the first. **1326 fenced rows at chapter 40 collapse to the 1316 the API
serves** (verified against the live endpoint). Reciprocal pairs `(s,t)` and `(t,s)` both
survive, because the graph is directed. The loss happens in the projection layer *after*
`query/fence.py` has returned its rows, so it is outside the fence's control and
invisible to it. Visible in §4 as the `parallel_edges` column (5 / 7 / 9 / 9).

**2. Identity edge relabelling.** The collapse in (1) can overwrite an identity edge's
relation type. At chapter 40, edge 1325 `SECRET_IDENTITY (14 -> 150)` is overwritten by
edge 1327 `REINCARNATION` on the same ordered pair, which is why `SECRET_IDENTITY` counts
read **1, 2, 2, 1** across chapters 10/20/30/40 instead of increasing monotonically.
Given rule #1 — the graph models revealed reader-knowledge — a reveal changing type in
the projection layer is the more serious of the two.

**3. Principal cast filter is a no-op on this work.** `rendered_view` and
`rendered_everyone` are identical at every chapter (74/369, 108/569, 127/709, 157/989 —
see §4). No drawable node in `the-ninth-house` has degree < 2, so the `degree >= 2`
clause in `visibleGraph` excludes nothing; the 206 → 157 node reduction is entirely
`buildViewModel`'s node-type drops, not cast reduction.

Neither (1) nor (2) was fixed in this phase. This phase changed no extraction, API or
frontend code.

One further observation from §3, not in BASELINE.md: **`GET /works/{slug}/status`
returns an unfenced `node_count`** (`repository.count_nodes` takes no chapter), so the
total entity count of a work is readable at any reading position. It leaks no element
and no name, so it is not counted as a fence violation — it is recorded as a side
channel this metric does not cover.

---

## 8. The reference annotation — provenance [MEASURED]

Sections 9–14 score v1 against the reference annotation in
`evidence/annotation/ch{09,17,37}.json`. **That annotation is model-generated**, and
every figure in those sections must be read in that light:

- **Produced by GPT-5**, one fresh session per chapter, single run each. No second
  model, no ensembling, no multi-pass self-review.
- **Human verification was partial**: paragraph indices, alias positions and evidence
  spans were checked against the source text and corrected by hand. The content
  judgements — which strings are entities, what type they are, which relations hold —
  were not independently re-derived by a human.
- **`ch09.json` was emitted 0-indexed** and was reindexed to match the 1-indexed
  paragraph numbering of `ch09_text.txt`.

Consequently every score in §9–§14 is **agreement between two systems**, StoryWeave v1
and GPT-5. It is **not accuracy against human ground truth**, and the unqualified phrase
"ground truth" is not used for it anywhere. All figures are given **per chapter** as
well as pooled. Full record: `evidence/annotation/PROVENANCE.md`.

Tools: `tools/eval_score.py` → `evidence/scores_v1.csv` (1,837 rows);
`tools/eval_errors.py` → `evidence/errors_v1.md`. Runner stdout verbatim in
`evidence/logs/eval_score.log` and `evidence/logs/eval_errors.log`.

### Validation of the reference files

Every check in the phase-2 brief was run: JSON parse; every relation endpoint present in
`entities[]`; every `evidence` string verbatim in the matching `ch<NN>_text.txt`; every
`type` one of v1's eight node types; every `relation` one of v1's 31 relation names;
every paragraph number in range. Quoted from `evidence/logs/eval_score.log`:

```
ch09.json — 22 entities, 21 relations, 7 paragraphs
  parses as JSON: yes
  all checks passed
  excluded from scoring: 0 entities, 0 relations, 0 aliases, 0 rejected_mentions
  uncertain records (excluded from all scoring): 4

ch17.json — 15 entities, 18 relations, 7 paragraphs
  parses as JSON: yes
  all checks passed
  excluded from scoring: 0 entities, 0 relations, 0 aliases, 0 rejected_mentions
  uncertain records (excluded from all scoring): 11

ch37.json — 9 entities, 12 relations, 9 paragraphs
  parses as JSON: yes
  all checks passed
  excluded from scoring: 0 entities, 0 relations, 0 aliases, 0 rejected_mentions
  uncertain records (excluded from all scoring): 8
```

**Zero validation failures, so zero records were excluded by validation.** Nothing was
repaired: the scorer opens these files read-only and has no repair path.

`uncertain` records — 4 / 11 / 8, 23 in total — are excluded from all scoring. They hold
free-text `item` / `paragraph` / `question` notes, not entity or relation records, so
the exclusion removes nothing from the scored sets; no score below draws on them.

### Match rules, stated verbatim

```
normalise(s): Unicode NFKC; replace the curly apostrophe U+2019 with '; casefold; strip
surrounding whitespace and the characters "'`.,;:!?()[]{}<>; collapse every internal
whitespace run to one space; drop a leading article 'the ', 'a ' or 'an '; drop a
trailing possessive "'s".
```

```
PRIMARY (strict): a v1 entity matches a reference entity iff normalise(v1.name) ==
normalise(reference.name) AND v1.type == reference.type. One-to-one: each reference
entity is consumed by at most one v1 entity. SECONDARY (alias-aware, reported
alongside, never instead): additionally allow a match when normalise(v1.name) equals the
normalisation of ANY of the reference entity's surface_forms, with the type still
required to be equal.
```

```
A v1 edge matches a reference relation iff their source entities matched, their target
entities matched, and the relation string is equal. Reference relations with
directed=true are matched on the ORDERED pair; with directed=false, either order is
accepted. Endpoints that could not be matched to a v1 entity make the relation
unmatchable, and it is counted as a reference-side miss.
```

**v1's side of the comparison.** A chapter's v1 entity set is every canonical node with
at least one row in `mentions` for that chapter (`repository.list_mentions`). The
relation set is reported **two ways**, neither privileged:

- `chapter_local` — edges with `first_seen_chapter == N`. Strict; it penalises v1 for
  relations it recorded in an earlier chapter.
- `cumulative` — every edge whose both endpoints are mentioned in chapter N, regardless
  of when v1 first recorded it. Generous; it credits v1 for relations this chapter's
  text may not support.

---

## 9. Entity detection — agreement [MEASURED]

Strict (name, type) match. Pooled and per chapter:

| chapter | v1 entities | reference entities | TP | FP | FN | P | R | F1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 21 | 22 | 11 | 10 | 11 | 0.5238 | 0.5000 | 0.5116 |
| 17 | 18 | 15 | 8 | 10 | 7 | 0.4444 | 0.5333 | 0.4848 |
| 37 | 9 | 9 | 6 | 3 | 3 | 0.6667 | 0.6667 | 0.6667 |
| **pooled** | 48 | 46 | 25 | 23 | 21 | **0.5208** | **0.5435** | **0.5319** |

Alias-aware variant (the secondary rule above), reported alongside:

| chapter | TP | FP | FN | P | R | F1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 12 | 9 | 10 | 0.5714 | 0.5455 | 0.5581 |
| 17 | 8 | 10 | 7 | 0.4444 | 0.5333 | 0.4848 |
| 37 | 7 | 2 | 2 | 0.7778 | 0.7778 | 0.7778 |
| **pooled** | 27 | 21 | 19 | **0.5625** | **0.5870** | **0.5745** |

Per node type, strict, pooled over the three chapters:

| node type | TP | FP | FN | P | R | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Character | 14 | 7 | 4 | 0.667 | 0.778 | 0.718 |
| Place | 9 | 8 | 3 | 0.529 | 0.750 | 0.621 |
| Organization | 2 | 1 | 5 | 0.667 | 0.286 | 0.400 |
| Ability | 0 | 0 | 1 | 0.000 | 0.000 | 0.000 |
| Concept | 0 | 3 | 3 | 0.000 | 0.000 | 0.000 |
| Event | 0 | 2 | 1 | 0.000 | 0.000 | 0.000 |
| Item | 0 | 1 | 1 | 0.000 | 0.000 | 0.000 |
| Title | 0 | 1 | 3 | 0.000 | 0.000 | 0.000 |

Per-chapter per-type figures are in `evidence/scores_v1.csv`. Sample sizes per type are
in the single digits — see §14.

---

## 10. Alias clustering — agreement [MEASURED]

Pairwise: over the surface strings **both** sides know (v1 saw them as mentions in that
chapter; the reference lists them as a name, surface form or alias), did the two systems
place each pair in the same cluster?

| chapter | shared surface strings | pairs | TP | FP | FN | TN | P | R | F1 | over-merges | under-merges |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 17 | 136 | 1 | 0 | 2 | 133 | 1.0000 | 0.3333 | 0.5000 | 0 | 2 |
| 17 | 14 | 91 | 1 | 0 | 1 | 89 | 1.0000 | 0.5000 | 0.6667 | 0 | 1 |
| 37 | 9 | 36 | 1 | 0 | 0 | 35 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |
| **pooled** | — | 263 | 3 | 0 | 3 | 257 | **1.0000** | **0.5000** | **0.6667** | **0** | **3** |

Over-merges and under-merges reported separately, as required: **0 over-merges, 3
under-merges**, all three listed in full:

- ch9 `captain` + `drask` — reference groups both under `Orin Drask`; v1 keeps `Captain`
  and `Drask` apart.
- ch9 `captain` + `orin drask` — same pair of clusters.
- ch17 `scribe` + `sorrel` — reference groups both under `Sorrel`; v1 keeps `scribe` and
  `Sorrel` apart.

The positive class is small (3 same-cluster pairs pooled), so these rates rest on very
few observations — see §14.

---

## 11. Relations — agreement [MEASURED]

### `chapter_local` (v1 edges with `first_seen_chapter == N`)

| chapter | v1 edges | reference relations | TP | FP | FN | micro-P | micro-R | micro-F1 | macro-F1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 106 | 21 | 4 | 102 | 17 | 0.0377 | 0.1905 | 0.0630 | 0.0212 (9 types) |
| 17 | 43 | 18 | 1 | 42 | 17 | 0.0233 | 0.0556 | 0.0328 | 0.0087 (11 types) |
| 37 | 18 | 12 | 0 | 18 | 12 | 0.0000 | 0.0000 | 0.0000 | 0.0000 (7 types) |
| **pooled** | 167 | 51 | 5 | 162 | 46 | **0.0299** | **0.0980** | **0.0459** | **0.0087** (15 types) |

### `cumulative` (every edge whose both endpoints are mentioned in chapter N)

| chapter | v1 edges | TP | FP | FN | micro-P | micro-R | micro-F1 | macro-F1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 123 | 5 | 118 | 16 | 0.0407 | 0.2381 | 0.0694 | 0.0214 (9 types) |
| 17 | 84 | 3 | 81 | 15 | 0.0357 | 0.1667 | 0.0588 | 0.0118 (13 types) |
| 37 | 31 | 1 | 30 | 11 | 0.0323 | 0.0833 | 0.0465 | 0.0156 (8 types) |
| **pooled** | 238 | 9 | 229 | 42 | **0.0378** | **0.1765** | **0.0623** | **0.0099** (17 types) |

**`FN` includes reference relations whose endpoints v1 never found** (38 of the 46
pooled `chapter_local` misses). Excluding them would score v1 only on the relations it
had already half-solved; the narrower figure is reported alongside in the CSV as
`micro_*_matchable_only` and in the log — pooled `chapter_local`, it would be FN=8
instead of FN=46.

### Per relation type, pooled, `chapter_local`

| relation | TP | FP | FN | F1 |
| --- | ---: | ---: | ---: | ---: |
| LocatedIn | 4 | 58 | 7 | 0.110 |
| RelatedTo | 1 | 81 | 15 | 0.020 |
| MemberOf | 0 | 2 | 9 | 0.000 |
| ParticipatedIn | 0 | 8 | 3 | 0.000 |
| HasTitle | 0 | 5 | 2 | 0.000 |
| LeaderOf | 0 | 3 | 1 | 0.000 |
| OwnsItem | 0 | 3 | 0 | 0.000 |
| Respects | 0 | 1 | 3 | 0.000 |
| TRANSMIGRATED_INTO | 0 | 1 | 0 | 0.000 |
| AffiliatedWith, Fears, HasAbility, Protects, Serves, Sibling | 0 | 0 | 1 each | 0.000 |

### Per tier

| tier | variant | TP | FP | FN | P | R | F1 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | chapter_local, pooled | 5 | 160 | 39 | 0.030 | 0.114 | 0.048 |
| 2 | chapter_local, pooled | 0 | 1 | 7 | 0.000 | 0.000 | 0.000 |
| 3 | chapter_local, pooled | 0 | 1 | 0 | 0.000 | 0.000 | 0.000 |
| 1 | cumulative, pooled | 9 | 223 | 35 | 0.039 | 0.205 | 0.065 |
| 2 | cumulative, pooled | 0 | 5 | 7 | 0.000 | 0.000 | 0.000 |
| 3 | cumulative, pooled | 0 | 1 | 0 | 0.000 | 0.000 | 0.000 |

Per-chapter tier figures are in `evidence/scores_v1.csv`.

---

## 12. Tier-3 identity — counts, not F1 [MEASURED]

Reported as counts, per the phase-2 brief.

| chapter | reference Tier-3 records | v1 Tier-3, `first_seen` here | v1 Tier-3, cumulative | matched |
| ---: | ---: | ---: | ---: | ---: |
| 9 | 0 | 0 | 0 | 0 |
| 17 | 0 | 0 | 0 | 0 |
| 37 | 0 | 1 | 1 | 0 |
| **pooled** | **0** | **1** | **1** | **0** |

**The required statement.** v1 **does** hold a `TRANSMIGRATED_INTO` edge at chapter 37 —
`Mira -TRANSMIGRATED_INTO-> Wanderer`, provenance `curated`, `revealed_chapter = 37`.
**The reference annotation for ch37 contains 0 Tier-3 records, so there is no matching
Tier-3 record in the reference.** The same is true of chapters 9 and 17: the reference
contains **no Tier-3 record of any kind, in any of the three chapters**. Its relations
are Tier 1 and Tier 2 only.

An F1 over Tier 3 is therefore undefined on the reference side (zero positives), which
is why the brief's instruction to report counts rather than F1 is the only thing that
can be reported here.

---

## 13. Significance ranking, and rejected mentions [MEASURED]

### Significance ranking

The reference marks each entity `significant: true/false`; that is the positive class,
transferred onto the v1 entity it matched under the strict rule. A v1 entity with no
reference counterpart is a negative. v1's entities are ranked by fenced degree at that
chapter.

| chapter | v1 entities ranked | positive | P@10 | P@20 | Recall@20 | MAP | AUC |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 21 | 5 | 0.4000 | 0.2500 | 1.0000 | 0.7014 | 0.7875 |
| 17 | 18 | 8 | 0.6000 | not measured | not measured | 0.6008 | 0.6500 |
| 37 | 9 | 6 | not measured | not measured | not measured | 0.9306 | 0.8333 |
| pooled | 48 | 19 | 0.4000 | 0.2500 | 0.2632 | 0.4414 | 0.3975 |

**"not measured" above means the chapter has fewer ranked entities than the cutoff** —
18 entities at ch17 and 9 at ch37 — and nothing was padded to reach it.

The pooled row is the three ranked lists **concatenated in chapter order**, which is not
a single ranking; its P@10 and P@20 are ch9's alone, and its AUC is depressed by the
concatenation rather than by any property of the ranking. It is reported because the
brief asks for a pooled figure, and it describes the concatenation and nothing more.

### Rejected mentions — a direct precision measure

The reference lists strings that should **not** become entities. v1 emitted **6 of 49**
pooled (rate 0.1224), either as an entity's canonical name or as a mention surface it
clustered into an entity.

| chapter | rejected strings scored | v1 emitted | rate |
| ---: | ---: | ---: | ---: |
| 9 | 14 | 2 | 0.1429 |
| 17 | 19 | 3 | 0.1579 |
| 37 | 16 | 1 | 0.0625 |
| **pooled** | **49** | **6** | **0.1224** |

All six, in full: `quiet` (ch9, v1 `Concept`), `gilded rooms` (ch9, v1 `Place`),
`ambition` (ch17, v1 `Concept`), `rooms` (ch17, surface folded into v1's `gilded rooms`),
`doors` (ch17, surface folded into v1's `Undercroft`), `Undercroft collapse` (ch37, v1
`Event`). Every one is a common noun or common-noun phrase; none is a proper noun.

---

## 14. Error analysis — summary [MEASURED]

Full analysis with the classification rules and examples: `evidence/errors_v1.md`,
generated by `tools/eval_errors.py`. Categories were read off the actual cases and then
written down as rules; each case is assigned to the first rule it satisfies, so the
categories partition the errors and the counts sum to the total.

**Entity false positives — 23** (v1 produced, reference did not):

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `type_disagreement` — same name, different node type | 8 | 2 | 5 | 1 |
| `not_in_reference` — the string appears nowhere in the reference | 8 | 4 | 4 | 0 |
| `reference_rejected_string` — explicitly in `rejected_mentions` | 4 | 2 | 1 | 1 |
| `reference_alias_kept_separate` — the reference folds it into another entity | 3 | 2 | 0 | 1 |

**Entity false negatives — 21** (reference has, v1 does not):

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `type_disagreement` — the mirror of the above | 8 | 2 | 5 | 1 |
| `partial_span_only` — v1 split or extended the span | 6 | 4 | 1 | 1 |
| `absent_from_v1_chapter` — no overlapping mention at all | 4 | 3 | 1 | 0 |
| `canonical_name_choice` — v1 clustered the string but named the entity differently | 3 | 2 | 0 | 1 |

**Relation false positives — 162** (`chapter_local`):

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `cooccurrence_fallback_RelatedTo` | 81 | 60 | 15 | 6 |
| `cooccurrence_type_pair_rule` | 79 | 41 | 27 | 11 |
| `curated_tier2_or_tier3` | 2 | 1 | 0 | 1 |

**Relation false negatives — 46** (`chapter_local`):

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `endpoint_not_found_by_v1` | 38 | 16 | 12 | 10 |
| `tier1_not_produced` | 5 | 1 | 2 | 2 |
| `tier2_social_not_produced` | 3 | 0 | 3 | 0 |

Two named cases from each category, and every case's full record, are in
`evidence/errors_v1.md` and `evidence/scores_v1.csv`.

---

## 15. Threats to validity — [MEASURED]

These apply to every figure in §8–§14. Every count cited below is one already reported in §8–§14 and produced by this session's runs; the limits they describe are properties of the measurement setup, not new measurements.

1. **The reference annotation is model-generated, not human-authored.** It was produced
   by GPT-5, one fresh session per chapter, single run each. Human involvement was
   limited to verifying and correcting paragraph indices, alias positions and evidence
   spans, and to reindexing `ch09.json` from 0- to 1-indexed. The content judgements —
   which strings are entities, what type each is, which relations hold — were not
   independently re-derived by a human.
2. **The scores measure agreement between two systems**, StoryWeave v1 and GPT-5. Where
   they disagree, nothing in this evaluation establishes which of the two is right. A
   disagreement is not by itself an error on v1's part, and these are not accuracy
   figures.
3. **Three chapters, one work, a single reference source.** Chapters 9, 17 and 37 of
   `the-ninth-house` only, annotated once, by one model. There is no second annotator,
   so no inter-annotator agreement can be computed and none is reported.
4. **The chapters are short** — 7, 7 and 9 paragraphs, 46 reference entities and 51
   reference relations in total. **Per-type sample sizes are very small**: five of the
   eight node types have fewer than 4 reference instances pooled, the alias metric rests
   on 3 same-cluster pairs pooled, and seven relation types (`LeaderOf`,
   `AffiliatedWith`, `Fears`, `HasAbility`, `Protects`, `Serves`, `Sibling`) have
   exactly one reference instance each. Single-digit denominators move these rates by large amounts, so
   per-type F1 values should not be compared with each other.
5. **Records in `uncertain` were excluded from scoring** — 4, 11 and 8, 23 in total.
   They are free-text notes rather than entity or relation records, so the exclusion
   removed nothing from the scored sets, but the questions they raise (for example
   whether `Warden's Discipline` is an ability or a professional quality) are exactly
   the cases where the two systems are most likely to disagree, and they are absent
   from the measurement.
6. **The relation comparison depends on a choice of chapter scope** with no neutral
   option. `chapter_local` penalises v1 for relations it first recorded in an earlier
   chapter; `cumulative` credits v1 for relations this chapter's text may not support.
   Both are reported; neither is the right answer.
7. **Relation scoring is bounded by entity matching.** 38 of the 46 pooled
   `chapter_local` relation misses are reference relations with an endpoint v1 never
   produced, so the relation figures largely restate the entity figures rather than
   measuring relation extraction independently.
8. **The reference contains no Tier-3 records at all**, so the identity layer — the
   feature this project treats as its showcase — is not exercised by this comparison in
   either direction.

---

## 16. Still not measured — [NOT MEASURED]

- **Spoiler-fence leak rate over the search surface** — needs a built vector index
  (`.chroma`), which does not exist in this checkout. Its fence key is chunk
  `chapter_ordinal <= n`.
- **Inter-annotator agreement on the reference** — there is only one reference source
  (§15.3), so none can be computed.
- **Any score against a human-authored reference** — the reference is model-generated
  (§8). Nothing in this report measures agreement with a human annotator.
- **Chapters other than 9, 17 and 37, and works other than `the-ninth-house`** — not
  annotated, so not scored.

### How chapters 9, 17 and 37 were chosen

By computed criteria, not by hand, in phase 1. Quoted from
`evidence/logs/make_annotation_template.log`:

- **Chapter 9 — early, introduces several entities.** *"15 entities are first revealed
  here (106 new edges), the most of any chapter in the first third excluding ch1."*
  Chapter 1 was excluded because every entity there is new by construction.
- **Chapter 17 — middle, dense with established relations.** *"27 of its 43 newly
  revealed edges connect entities that were ALREADY revealed before this chapter — the
  highest such count in the middle third."*
- **Chapter 37 — late, identity reveal.** *"carries an identity reveal. All Tier-3/Killed
  edges in the work: ch5:ALIAS, ch10:SECRET_IDENTITY, ch16:ALIAS, ch20:SECRET_IDENTITY,
  ch28:REINCARNATION, ch34:REINCARNATION, ch37:TRANSMIGRATED_INTO. Chosen the latest one
  in the final third."* The database contains **no** `Killed` edges, so "a death" is
  represented only by the text, not by a graph element.

The annotation pack itself — `GUIDELINES.md` (generated from v1's own code and
database), the three numbered chapter texts and the three empty templates — is in
`evidence/annotation/`.

---

## Reproducing

Never run these in parallel.

```
# phase 1
.venv/Scripts/python     tools/eval_fence.py               # → evidence/fence_leaks.csv
.venv/Scripts/python     tools/eval_salience.py            # → evidence/salience_v1.csv
.venv-ml/Scripts/python  tools/eval_performance.py         # → evidence/performance_v1.csv
.venv/Scripts/python     tools/make_annotation_template.py # → evidence/annotation/

# phase 2 (eval_errors reads the same inputs, not the CSV, so order does not matter)
.venv/Scripts/python     tools/eval_score.py               # → evidence/scores_v1.csv
.venv/Scripts/python     tools/eval_errors.py              # → evidence/errors_v1.md
```

**Set `STORYWEAVE_HF_HOME=F:\Dev\shared\hf-cache` before re-running the performance
tool.** Without it, `storyweave/config.py` falls back to `<repo>/.hf-cache` and silently
re-downloads 613 MB of weights back into the repo.

Gates at the end of phase 2, run in `.venv`:

- `ruff check` on the six evaluation tools — `All checks passed!`
- `mypy` (strict, covers `tools/`) — `Success: no issues found in 76 source files`
- `pytest` — `152 passed, 6 skipped, 2 warnings in 3.38s`

`ruff check .` over the whole repo still reports **20** pre-existing `E501`/`I001`
findings in the older `tools/` scripts (`capture.py`, `graph_metrics.py`,
`plot_growth.py`, `run_evidence.py`, `verify_shots.py`). Those predate this evaluation
and were left alone; the six tools added by it are clean.
