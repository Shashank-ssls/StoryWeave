# R1 — co-occurrence off: the measured result

**What was measured.** The same answer key, the same scorer, the same match rule, the same
entities — the only difference is that every `extraction_method='rule'` edge is gone. So
the deltas below are attributable to the co-occurrence builder and to nothing else.

| field | value |
| --- | --- |
| date | 2026-09-28 |
| branch | `retrofit/v2-core`, phase R1 |
| baseline (v1) | `evidence/v1_ninth_house.db`, rerun recorded in `R0_baseline_rerun.md` |
| rule-off DB | `evidence/retrofit/r1_rule_off.db`, built by `tools/make_rule_off_db.py` |
| scorer | `tools/eval_score.py`, unchanged; annotation `evidence/annotation/ch{09,17,37}.json`, unchanged |
| work | `the-ninth-house` (`work_id = 2`), 40 chapters |
| LLM | off. Nothing was re-extracted; no model ran |

Logs, verbatim: `logs/R1_make_rule_off_db.log`, `logs/R1_eval_score.log`,
`logs/R1_graph_metrics.log`. Every figure below is **[MEASURED]**.

> Scores are **agreement** with a model-generated (GPT-5) reference annotation with
> hand-verified indices, not accuracy against human ground truth
> (`evidence/annotation/PROVENANCE.md`).

---

## 1. The headline, stated plainly

**Relation micro-F1 went from 0.0459 to 0.0000. Switching off co-occurrence made the
measured F1 worse, not better.**

```
v1        --- pooled [chapter_local] --- TP=5 FP=162 FN=46
            micro P=0.0299 R=0.0980 F1=0.0459   macro-F1 over 15 relation types: 0.0087

rule-off  --- pooled [chapter_local] --- TP=0 FP=2 FN=51
            micro P=0.0000 R=0.0000 F1=0.0000   macro-F1 over 14 relation types: 0.0000
```

**All five of v1's true positives were rule edges, and all five were lost.** They were 4
`LocatedIn` and 1 `RelatedTo` — the never-drop fallback. The rule scored 5 hits out of
1307 attempts; deleting the 1307 deletes the 5. No curated Tier-2/Tier-3 edge in this
database matched the reference at all, in either scope, before or after.

This is the negative half of the result and it is not softened: R1 alone does not improve
F1, because F1 needs true positives and nothing in R1 produces any. The retrofit's
projection that removing co-occurrence raises relation F1 is **not supported by this
measurement**; what the measurement supports is the *precondition* for raising it.

## 2. What actually improved: precision's denominator

| quantity, pooled `chapter_local` | v1 | rule-off | change |
| --- | ---: | ---: | ---: |
| false positives | 162 | **2** | **−160 (−98.8%)** |
| true positives | 5 | 0 | −5 |
| false negatives | 46 | 51 | +5 |
| edges the scorer saw (ch 9 / 17 / 37) | 106 / 43 / 18 | 1 / 0 / 1 | −165 |

| pooled `cumulative` | v1 | rule-off |
| --- | ---: | ---: |
| TP / FP / FN | 5 / 229 / 42 | 0 / 6 / 51 |
| micro P / R / F1 | 0.0378 / 0.1765 / 0.0623 | 0.0000 / 0.0000 / 0.0000 |
| edges the scorer saw (ch 9 / 17 / 37) | 123 / 84 / 31 | 2 / 2 / 2 |

Per tier, pooled `chapter_local` — this is the cleanest statement of what R1 did:

| tier | v1 TP/FP/FN | rule-off TP/FP/FN |
| --- | ---: | ---: |
| 1 (co-occurrence) | 5 / **160** / 39 | 0 / **0** / 44 |
| 2 (curated social) | 0 / 1 / 7 | 0 / 1 / 7 |
| 3 (curated identity) | 0 / 1 / 0 | 0 / 1 / 0 |

Tier-1's 160 false positives are gone and nothing else moved. The 2 surviving false
positives are both hand-curated: one `Respects` (Tier 2) and one `TRANSMIGRATED_INTO`
(Tier 3). They are a curation question, not an extraction one, and are out of R1's scope.

**Read the right way round: v1 asserted 167 relations in the three scored chapters and 162
of them were wrong. The rule-off graph asserts 2. A graph that says almost nothing is a
worse scorer and a better foundation — every edge R4 adds now lands on an empty field
instead of being buried under 1307 proximity guesses.**

## 3. Where the relations went, per relation type

Pooled `chapter_local` false positives, v1 → rule-off:

| relation | v1 FP | rule-off FP |
| --- | ---: | ---: |
| RelatedTo | 81 | 0 |
| LocatedIn | 58 | 0 |
| ParticipatedIn | 8 | 0 |
| HasTitle | 5 | 0 |
| LeaderOf | 3 | 0 |
| OwnsItem | 3 | 0 |
| MemberOf | 2 | 0 |
| Respects | 1 | 1 |
| TRANSMIGRATED_INTO | 1 | 1 |

The reference's own misses are unchanged in kind and now unmasked: 11 `LocatedIn`, 9
`MemberOf`, 16 `RelatedTo`, 3 `ParticipatedIn`, 2 `HasTitle` and one each of
`AffiliatedWith`, `Fears`, `HasAbility`, `LeaderOf`, `Protects`, `Serves`, `Sibling` are
false negatives — 51 in total, of which 44 are Tier-1-shaped. That list is R4's and R5's
work order.

## 4. Density — [MEASURED]

`tools/graph_metrics.py --config api_payload`, verbatim:

```
r1_rule_off | api_payload | the-ninth-house | 10      | 90    | 10    | 10    | 0 | 0 | 0.2222 | 0.0 | 4 | 0.002497 | 78  | 6
r1_rule_off | api_payload | the-ninth-house | 20      | 138   | 14    | 14    | 0 | 0 | 0.2029 | 0.0 | 4 | 0.001481 | 122 | 9
r1_rule_off | api_payload | the-ninth-house | 30      | 167   | 17    | 17    | 0 | 0 | 0.2036 | 0.0 | 5 | 0.001226 | 148 | 11
r1_rule_off | api_payload | the-ninth-house | 40      | 206   | 18    | 18    | 0 | 0 | 0.1748 | 0.0 | 5 | 0.000852 | 186 | 11
```

(chapter | nodes | edges | distinct_pairs | parallel_edges | self_loops | mean_degree |
median_degree | max_degree | edge_density | isolated_nodes | degree1_nodes)

Side by side at ch40:

| metric at ch40 | v1 | rule-off |
| --- | ---: | ---: |
| nodes served | 206 | 206 |
| edges served | 1316 | **18** |
| mean degree | 12.78 | 0.17 |
| median degree | 8.0 | **0.0** |
| max degree | 121 | 5 |
| edge density | 0.0619 | 0.00085 |
| **isolated nodes** | 0 | **186 of 206 (90.3%)** |
| degree-1 nodes | 1 | 11 |

**186 of 206 nodes at ch40 have no edge at all, and the median node degree is 0.** This
was expected and is stated as the finding it is: v1's graph was connected only because
co-occurrence connected everything to everything. Twenty nodes carry the whole remaining
graph. **This is the recall hole R4 (cited relation extraction) and R5 (LLM recall pass)
exist to fill; R1 is the measurement that sizes it, not a fix.** Nothing about the current
rule-off graph is shippable as a reader experience, and R7 must not be run against it.

## 5. D2 is now the entire projection loss — [MEASURED]

| quantity, ch40 | value |
| ---: | --- |
| edge rows in the rule-off DB (`work_id = 2`) | **19** |
| rows passing the fence at ch40 | **19** |
| edges served by `/graph?n=40` | **18** |

Relations in the DB vs served:

```
DB     : ALIAS 2, Mentor 3, Parent 2, Protects 1, REINCARNATION 2, Respects 1,
         Rival 1, SECRET_IDENTITY 2, Serves 3, Sibling 1, TRANSMIGRATED_INTO 1   (19)
served : ALIAS 2, Mentor 3, Parent 2, Protects 1, REINCARNATION 2, Respects 1,
         Rival 1, SECRET_IDENTITY 1, Serves 3, Sibling 1, TRANSMIGRATED_INTO 1   (18)
```

One row is lost and it is **`SECRET_IDENTITY`** — edge 1325 on ordered pair 14 → 150,
overwritten by `REINCARNATION` (edge 1327) in the `nx.DiGraph` projection. In R0 this
defect (D2) was one of ten collapsed rows and nine of the ten were co-occurrence junk.
With the junk gone, **D2 is 100% of the projection loss, and the single row it destroys is
an identity reveal** — the most consequential element type in the product. R4's multigraph
fix is now load-bearing, not cosmetic.

## 6. Two things that did NOT change, as a control — [MEASURED]

Deleting edges must not move entity or alias agreement. It did not:

| metric | v1 | rule-off |
| --- | --- | --- |
| entity F1, pooled strict | `TP=25 FP=23 FN=21 P=0.5208 R=0.5435 F1=0.5319` | identical |
| entity F1, pooled alias-aware | `TP=27 FP=21 FN=19 P=0.5625 R=0.5870 F1=0.5745` | identical |
| alias clustering, pooled | `TP=3 FP=0 FN=3 P=1.0000 R=0.5000 F1=0.6667` | identical |
| entities per chapter (9/17/37) | 21 / 18 / 9 | identical |
| rejected-string emission rate | 6 of 49 (0.1224) | identical |
| nodes served (ch 10/20/30/40) | 90 / 138 / 167 / 206 | identical |

This is the like-for-like proof: the entity half of the system is untouched, so §1–§5 are
about edges only.

## 7. One thing that changed and should not be ignored — [MEASURED]

The importance-ranking metric got worse:

| pooled ranking metric | v1 | rule-off |
| --- | ---: | ---: |
| P@10 | 0.4000 | **0.3000** |
| MAP | 0.4414 | **0.3668** |
| AUC | 0.3975 | 0.3938 |
| P@20 / Recall@20 | 0.2500 / 0.2632 | unchanged |

The scorer ranks entities by **fenced payload degree at that chapter**
(`tools/eval_score.py:293`), so removing edges removes the ranking signal. **This is a
direct warning for R6:** per-chapter salience must not be computed from co-occurrence
degree, because after R1 there is almost no degree to compute from. R6 should rank on
mention frequency up to chapter *n* (and cited-edge degree once R4 supplies edges), never
on the rule builder's degree. Recorded here so R6 does not rediscover it by shipping a
broken cast dial.

## 8. What R1 changed in the code

- `RelationConfig.cooccurrence_enabled: bool = False` — new, **off by default**
  (`storyweave/ingest/work_config.py`). The builder stays in the tree; the flag makes it
  reproducible evidence rather than dead code, per retrofit rule 5.
- `build_relationships` returns an empty report when the flag is off
  (`storyweave/graph/builder.py`), and its docstring now records why the default is off.
- **`repo.clear_edges(work_id)` was deleting every edge of every tier on each Tier-1
  rebuild** — including curated Tier-2/Tier-3. New `clear_edges_by_method` in
  `db/repository.py` (all SQL stays there) scopes the rebuild's delete to
  `extraction_method = 'rule'`, so toggling or re-running the rule builder can never
  destroy a relex, LLM or curated edge. `clear_edges` is kept, with a docstring warning
  that it is the blunt variant. **This was a live data-loss bug**: re-running `relate` on
  the seeded Ninth House would have silently wiped its 19 hand-curated edges.
- Four existing tests in `test_relate.py` and two in `test_relex.py` now pass an explicit
  rule-enabled config, because they are tests *of the rule*. No test's assertions were
  weakened.
- New: `test_cooccurrence_disabled_by_default_creates_no_edges` and
  `test_rule_rebuild_does_not_delete_other_producers_edges`.
- New: `tools/make_rule_off_db.py`, which derives the rule-off DB by copying the frozen
  baseline and deleting only that work's `rule` edges. It verifies afterwards that the
  deleted count matches, that no `rule` edge survived, that non-rule edges are unchanged,
  that the other work (seeded Hollow Crown, 11 `rule` + 3 `llm` edges) is untouched, and
  that `PRAGMA integrity_check` is `ok`. The source DB is opened read-only.

The derived DB is gitignored (`*.db`) because it is fully regenerable from a committed
database by a committed script; the script is the artifact.

## 9. Stop conditions — none tripped

| stop condition | status |
| --- | --- |
| `tools/check_local_env.py` fails | passes, 10/10, both venvs |
| any fence violation | **0 over 17,471 elements** on the rule-off DB, detector verified to fire (`logs/R1_eval_fence.log`, 8,424 queries). No fence code changed; the element count falls with the edges, from 105,243 to 17,471 |
| any alias over-merge | 0 (unchanged, §6) |
| any SAME_AS false positive | 0. The one Tier-3 FP is `TRANSMIGRATED_INTO`, present in v1 too, from curation |
| ch40 default graph < 10 or > 40 nodes | not applicable — no default-cast filter exists until R6 |
| R5 lowering precision by > 0.10 | not applicable |

## 10. Honest reading of R1

R1 delivered a real measurement and a **worse headline number**. Reported as it is:
micro-F1 0.0459 → 0.0000, because the five accidental true positives were themselves
co-occurrence edges. What R1 bought is the 160 false positives it removed and the clean
statement of what remains: 51 missing relations and 186 isolated nodes at ch40. That is
the work R4 and R5 have to do, now sized and attributable rather than hidden inside a
graph that connected everything to everything. It also fixed one latent data-loss bug and
turned one hidden defect (D2) into the only remaining projection loss, which is what makes
R4's fix testable.
