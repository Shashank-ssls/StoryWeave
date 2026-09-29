# R4c — relex grounded on known entities

| field | value |
| --- | --- |
| date | 2026-09-29 |
| branch | `retrofit/v2-core`, phase R4c |
| output DB | `data/retrofit/ninth_house_r4c.db`, from `ninth_house_r4b_entities.db` |
| model | `knowledgator/gliner-relex-base-v1.0`, CPU, `HF_HUB_OFFLINE=1`, nothing downloaded |
| settings | **unchanged from R4's pre-registration** — ner 0.3, rel 0.6, same cue lists, same kin guard, same validator. No tuning |
| pre-registration | `docs/retrofit/RETROFIT_PROGRESS.md`, commit `5d25d3a` |
| LLM | off |

Logs: `logs/R4c_api_probe.log`, `logs/R4c_api_probe2.log`, `logs/R4c_build_db.log`,
`logs/R4c_eval_score_*.log`, `logs/R4c_recall_audit.log`, `logs/R4c_report.log`,
`logs/R4c_baseline_r4b.log`. Screenshots: `shots/R4c/`. Every figure **[MEASURED]**.

---

## 0. Headline, against the pre-registration

| quantity | pre-registered | measured | verdict |
| --- | --- | ---: | --- |
| ring-1 edges at ch40 | 4 – 25 | **4** | inside band, at the floor |
| ring-2 edges at ch40 | 60 – 150 | **64** | inside band, near the floor |
| STATED micro-F1, 12-relation key | 0.05 – 0.25 | **0.0000** | **MISSED — below the band** |

**R4c grounded 30 more spans and produced 4 more edges. It converted zero gold relations
and produced zero default-view edges.** The prediction that ring-2 "should grow the most"
was directionally right (+4 of the +4) and wrong in magnitude.

---

## 1. Which path, and why — the primary path was measured and rejected

The R4c brief asks whether the installed GLiNER-RelEx accepts caller-supplied entity
spans. It **has the argument and ignores it.**

`GLiNER.inference(...)` takes `input_spans`, documented as *"Input entity spans to limit
predictions to. Each span is a dict with 'start' and 'end' character positions."* Supplying
it changes nothing (`tools/r4c_api_probe2.py`):

| NER mode | entities, free | entities, with `input_spans` | result |
| --- | ---: | ---: | --- |
| `flat_ner=False` | 12 | 12 | **identical → ignored** |
| `flat_ner=True` | 6 | 6 | **identical → ignored** |

Supplying `['Orin Drask', 'Salt Quarter watch', 'Juno Stray']` still returns all twelve
free-NER spans including `Salt Quarter`, `watch`, `him` and `Warden-Captain`. Accepted,
not honoured.

**So R4c used the FALLBACK: snapping.** relex runs free, and each returned span is snapped
to the stored mention it overlaps most, within the same chapter. Ties go to the shortest
candidate, so a span inside `Salt Quarter` grounds to the Place rather than to the longer
Organization containing it. The exact-surface lookup still runs first, which makes R4c a
strict superset of R4b: every span that grounded before grounds to the same node, and
snapping only ever rescues one that failed.

**Fenced by construction.** The candidate list for a chunk in chapter *n* is built from
`fence.visible_nodes(repo, work_id, n)`, so a mention of an entity first revealed at *n+3*
is not a snapping target at *n*. Without that, the snapper would be a side channel
leaking a later reveal into an earlier chapter's edge.

### A second thing the probe corrected

R4b's report said relex "sees `Salt Quarter` and never proposes the full span". **That is
wrong.** Free NER *does* return `Salt Quarter watch` as an organization — it is in the
probe output above. The real failure was narrower: relations were proposed between spans
like `him`, `watch` and `Drask` that no stored surface matched. The diagnosis was right
about the *stage* and wrong about the *mechanism*, and the fix still follows from the
corrected version.

---

## 2. What changed in the build

```
R4b : 306 proposals -> 64 edges (+61 reinforcements), 181 rejected
R4c : 306 proposals -> 68 edges (+75 reinforcements), 163 rejected; snapped 30, unsnapped 125
```

| | R4b | R4c |
| --- | ---: | ---: |
| edges | 64 | **68** |
| STATED | 37 | **40** |
| `ENDPOINT_NOT_STORED` rejections | 137 | **115** |
| `DOMAIN_RANGE` | 44 | 47 |
| `SELF_LOOP` | 0 | 1 |
| spans rescued by snapping | — | **30** |

### The 125 endpoints that still ground to nothing — this is the finding

55 distinct surfaces. The top of the list explains why snapping hit a ceiling:

| n | surface | what it is |
| ---: | --- | --- |
| 14 | `She` | pronoun |
| 6 | `she` | pronoun |
| 6 | `secret` | common noun |
| 6 | `names` | common noun |
| 4 | `birds` | common noun |
| 4 | `realm` | common noun |
| 3 | `I`, `He` | pronouns |
| 3 | `uncle`, `room`, `box`, `weight`, `name`, `something`, `somewhere`, `somewhere else` | common nouns |

**The residue is pronouns and common nouns, not missed entities.** Snapping cannot fix
`She`, because there is no mention at those offsets to snap to — resolving it is
*coreference*, which the retrofit explicitly cut. The rest (`secret`, `birds`, `realm`,
`something`) are relex proposing relations between things that are not entities at all;
those *should* be refused, and are.

---

## 3. Scores — [MEASURED]

All runs exclude curated seeds (`--exclude-method curated`).

| run | key | grade | TP | FP | FN | micro-F1 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| **headline** | 12-relation | STATED | 0 | 3 | 23 | **0.0000** |
| diagnostic | 12-relation | STATED+INFERRED | 0 | 3 | 23 | 0.0000 |
| like-for-like | original v1 key | all | 0 | 3 | 51 | 0.0000 |

Identical to R4b in every cell. The diagnostic again shows the both-names rule costing
**zero** recall: the loss is not at the grade.

### Recall accounting, R4b vs R4c — nothing moved

| stage | R4 | R4b | **R4c** |
| --- | ---: | ---: | ---: |
| `NOT_IN_THE_TWELVE` | 28 | 28 | **28** |
| `NO_PROPOSAL` | 12 | 18 | **18** |
| `ENTITY_MISSING` | 6 | 0 | **0** |
| `WRONG_TYPE` | 2 | 2 | **2** |
| `VALIDATOR_REJECTED` | 1 | 1 | **1** |
| `GRADE_INFERRED` | 1 | 1 | **1** |
| `FOUND` | 1 | 1 | **1** |

R4b moved 6 relations from `ENTITY_MISSING` to `NO_PROPOSAL`. **R4c moved none.** The 30
snapped spans were all on pairs that were not gold relations in the three scored chapters.

---

## 4. Ring counts and the default view

| chapter | nodes | edges | ring1 | ring2 | STATED | INFERRED |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 86 | 22 | 3 | 19 | 11 | 11 |
| 20 | 134 | 28 | 3 | 25 | 14 | 14 |
| 30 | 153 | 47 | 3 | 44 | 27 | 20 |
| 40 | 191 | 68 | **4** | **64** | 40 | 28 |

Per relation at ch40: `LOCATED_IN` 22 (22 STATED), `MEMBER_OF` 23 (6), `OWNS` 17 (11),
`SERVES` 4 (1), `LEADS` 2 (0). **`KIN_OF`, `ROMANTIC_WITH`, `ALLY_OF`, `ENEMY_OF`,
`MENTOR_OF`, `KILLED`, `SAME_AS`: zero.**

> **Correction carried from the pre-registration:** R4 and R4b both said "all 64 edges are
> ring 2". Wrong — `SERVES` is a ring-1 relation, so there are **4 ring-1 edges**. The
> substantive claim survives (no *social* graph reaches the reader) but the number was
> stated wrongly and is corrected here.

### Default view at ch40 — Characters only, cast 20, STATED

**0 edges. 20 of 20 cast members isolated.** Unchanged from R4b.

This is a measurement projection defined in `tools/r4c_report.py` (the API has no cast
parameter — that is R6). It ranks by mentions up to chapter *n* only, never a book-wide
rank, per retrofit rule 7.

---

## 5. Demo check (Rule Zero) — screenshots inspected, not assumed

Captured with `playwright-core` driving the **system Chrome** (`channel: "chrome"`), no
browser downloaded, harness in `.local/pw` on F:. App served from `frontend/dist` by the
API on port 8017 against `ninth_house_r4c.db`. **Zero console errors.** Files in
`evidence/retrofit/shots/R4c/`.

**A correction I have to make first.** I said earlier in this session that the frontend has
no cast-size or type controls. **It has both** — `show-people`, `show-orders`
("Orders & houses"), `show-places` ("Places & Relics"), and `cast-principal` /
`cast-everyone`. Running the app is what found that; reading the source had not.
Consequently the two views the brief asks for do not map cleanly, because **"Groups" is ON
by default** (`SHOW_ALL = {people: true, orders: true, places: true}`,
`frontend/src/graph/stemmaModel.ts:12`). So the informative pair is captured instead.

### `03_web_ch40_default.png` — the app's own defaults

What a first-time viewer sees: the view opens **focused on one character, Sorrel, at 1
step** — not the whole graph. Roughly **17 dots**: Sorrel highlighted in cream at the
centre, seven dim brown people (Thorne, Thessaly, Corwin, Vesper, Ione, Cassian, the
Regent), and the rest bright rings and squares for organizations, places and items
(The Chancery, the Council, The Choir, Aldenreach, The Undercroft, household, jewelry,
ledger).

**Lines: many — roughly two dozen thin strokes — and NOT ONE HAS A LABEL.** Several run
off the edge of the canvas to nodes that are not drawn. The right-hand panel lists
Sorrel's ties as *"the Council — linked · ch. II"*, *"The Choir — linked · ch. V"*: the
word is **"linked"**, never `MEMBER_OF` or `LOCATED_IN`. So even the 68 relations that do
exist reach the reader as untyped string.

Node labels themselves are readable and well set; the typography is not the problem.

### `04_web_ch40_people_only.png` — the retrofit's intended default (rule 2)

**12 dots. Zero lines.** A tidy grid of names — Sorrel, Thessaly, Mira, Ione, Cassian,
Thorne, Vesper, Corwin, Magistrate Wyle, Oswin, the Regent — floating unconnected on an
empty canvas. This is the measured "0 default-view edges" rendered, and it is the single
most useful image this phase produced.

### `05_web_ch40_people_plus_groups.png` — People + Orders & houses

Adds the organizations back and with them the `MEMBER_OF` / `SERVES` lines. Still no edge
labels.

---

## 6. Verdict

**Is R5 (LLM) still needed? YES.** Default-view edges at ch40 = **0**, far below the
threshold of 10. Two phases of grounding work (R4b entities, R4c snapping) moved that
number by zero. The corpus's character-to-character relations are not being stated by
relex at any grounding quality, so a model that reads prose is the remaining lever.

**Is either screenshot showable to a non-technical reviewer as-is? NO — neither.**
`04` shows twelve disconnected dots, which reads as a broken app rather than a sparse one.
`03` shows a dense unlabelled web where every tie says only "linked", so a reviewer can
see that things connect but never *how* — and the first thing they would ask ("how are
these two related?") is the one thing the screen cannot answer. The nearest showable
artefact today is `05`, and it still fails the edge-label test.

**One qualification on R5, from §2's residue.** The largest single category of ungrounded
endpoints is pronouns (`She` ×14, `she` ×6, `He`, `I`). Those are coreference, not model
recall. An LLM pass would resolve them incidentally, but so would a much cheaper coref
step — worth weighing before committing to R5's budget.

---

## 7. Viva defense

R4c is a negative result delivered against a pre-registered band, and its value is that it
closes off a hypothesis cheaply and by measurement rather than argument: the documented
`input_spans` API is accepted and silently ignored by this build, proven by a byte-identical
entity list under both NER modes, so the primary design was abandoned before it was
written. The fallback was built, it worked as designed — 30 spans rescued, 22 fewer
`ENDPOINT_NOT_STORED` refusals — and it still converted nothing, which localises the
remaining loss precisely: 125 ungrounded endpoints that are pronouns and common nouns, not
missed entities. Two of my own earlier claims were corrected here against evidence rather
than left standing: that relex never proposes the long organization span, and that the
frontend has no type or cast controls. The screenshot of twelve unconnected dots is the
phase's real deliverable, because it converts "micro-F1 0.0000" into something a
non-technical reviewer can judge in one second.
