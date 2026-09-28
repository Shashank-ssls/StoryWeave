# R3 — four drawable types, chapter-gated entity labels, title linking

| field | value |
| --- | --- |
| date | 2026-09-28 |
| branch | `retrofit/v2-core`, phase R3 (R0–R2 complete) |
| re-extraction | `data/retrofit/ninth_house_r3.db`, built by `tools/build_r3_db.py` |
| model | `urchade/gliner_small-v2.1`, CPU, from `F:\Dev\shared\hf-cache` (nothing downloaded) |
| LLM | off. No Ollama, no API. Title linking is regex apposition, no model |
| frozen DB | never written. Read-only, hash re-verified |

Logs, verbatim: `logs/R3_build_db.log`, `logs/R3_eval_score_4type.log`,
`logs/R3_eval_fence.log`, `logs/R3_eval_fence_frozen.log`.
Every figure is **[MEASURED]**.

---

## 0. Scoring note — READ FIRST

**The 4-type entity score below is computed against a 4-TYPE PROJECTION of the annotation
and is a DIFFERENT ANSWER KEY from v1's.** The projection drops every reference entity
whose type the retrofit no longer draws, via `LEGACY_TYPE_MAP` — 8 of 46 reference
entities across the three chapters:

```
4-TYPE PROJECTION ch09: dropped 3: 'Warden-Captain' (Title), 'Warden' (Concept), "Warden's Discipline" (Ability)
4-TYPE PROJECTION ch17: dropped 3: 'Vell Masque' (Event), 'Lord' (Title), 'Scribe' (Title)
4-TYPE PROJECTION ch37: dropped 2: 'Wanderer' (Concept), 'Choir initiate' (Concept)
```

**Its F1 must never be reported as a delta against v1's 0.532.** Fewer reference entities
and a different type vocabulary make the two numbers incommensurable: the projected key is
easier in that the hardest types are gone, and harder in that there is nowhere for a
mis-typed entity to hide. R3's figures stand on their own.

**The scorer's default behaviour is provably unchanged.** The projection is an opt-in
`--four-type-projection` flag, implemented by excluding reference indices rather than
rewriting the annotation or the match rule. Proof: re-running the scorer with no flags
against the frozen DB reproduces `R0_eval_score.log` **byte for byte** — the only
difference in the whole diff is the output filename, and the row count is 1837 in both.

## 1. The mapping: two vocabularies, no migration — [MEASURED]

Nothing was migrated. `NodeType` still has all eight values, the `nodes.type` CHECK
constraint is unchanged, and `Node(**row)` still validates every historical row.
`GraphNodeType` adds the four the graph draws, and `LEGACY_TYPE_MAP` in `db/models.py` is
the single place recording each old type's fate:

| stored type | fate | consequence |
| --- | --- | --- |
| Character, Organization, Place, Item | `GRAPH_NODE` | drawn |
| Ability, Concept, Event | `NOT_A_NODE` | rows kept and searchable via `mentions`; never served in a graph payload; never written again |
| Title | `BECOMES_LABEL` | an `entity_labels` row on the person the text links it to; otherwise not served |

Three independent enforcement points, so no single omission leaks a legacy type:

| # | where | guarantee |
| --- | --- | --- |
| (a) | `nlp/labels.py` prompts 4 types; an import-time assert pins it | nothing new is **created** |
| (b) | `Repository.add_node` raises on a non-graph type | nothing new is **stored** |
| (c) | `list_graph_nodes_revealed` adds `type IN (...)` **after** the fence clause | nothing legacy is **served** |

(c) keeps the two clauses visibly separate, each with its own comment naming it FENCE
(safety) or DISPLAY (presentation). `test_display_filter_never_widens_the_fence` asserts
the drawn set is a subset of the fenced set at every chapter, so the display clause can
only ever narrow.

## 2. Compatibility — the part that had to not break — [MEASURED]

| check | result |
| --- | --- |
| frozen v1 DB loads all 206 nodes through pydantic | **pass** |
| frozen v1 DB fences identically | **0 violations over 95,530 elements**, detector verified to fire |
| frozen v1 DB **serves**: no phantom nodes, every served edge's endpoints served | **pass** |
| Hollow Crown seeded rows byte-identical | **pass** — digest `e73a69c0…c482`, recorded before any R3 code was written and asserted in a test |
| frozen DB SHA-256 after the phase | `c7264c16…d946ff`, unchanged |

The frozen DB's element count falls from 105,243 to 95,530 purely because the display
clause stops serving 4 legacy types' nodes and their edges — fewer elements to audit, same
zero.

### One deviation from rule I2, stated plainly

`tests/test_demo_seed.py::test_all_eight_node_types_present_by_final_chapter` asserted that
the Hollow Crown **payload** contains all eight types. R3's decision (c) makes that
assertion state the opposite of the intended behaviour, so it could not be kept as written.
It is now `test_all_eight_node_types_stored_but_only_four_are_drawn`, asserting **both**
halves: the fixture still stores one node of each of the eight types and they all still
pass the fence, *and* only the four drawable ones reach the client.

This is strictly stronger than the original. **No seeded data was touched** — the fixture's
rows are byte-identical and that is asserted by digest. What changed is a test's contract,
not the fixture, and it changed because the phase's whole purpose is to change what is
drawn. Flagged rather than buried.

### Two real bugs R3's display filter exposed and fixed

1. **Phantom nodes.** `build_graph` called `nx.add_edge` for every fenced edge, and
   networkx silently creates any missing endpoint. With legacy types no longer drawn, four
   attribute-less nodes reappeared in the Hollow Crown payload and failed response
   validation (`nodes.9.data.label Field required`). Edges whose endpoints are not drawn
   are now skipped. This can only narrow the payload; the fence has already decided
   visibility.
2. **Pre-R3 databases crashed the new label reads.** The frozen baseline has no
   `entity_labels` table and is opened read-only, so it cannot be migrated on the fly.
   `has_entity_labels_table()` probes once and the label reads return empty for such a
   database, with the graph falling back to `nodes.name`. Without this the frozen DB raised
   `no such table: entity_labels` on every graph request.

## 3. entity_labels is a fence surface — [MEASURED]

New table, reveal-stamped like every other graph element, with the both-rule applied as
for node properties (a name for a character the reader has not met is still a spoiler).

**Audited by the harness, not just unit tests.** `tools/eval_fence.py` now inspects the
label surface, and the R3 database run reports:

```
total queries issued:    7640
total elements inspected: 20439
    arc_name: 200
    detail_entity: 4758
    entity: 4758
    graph_node: 4758
    graph_node_label: 5965
TOTAL VIOLATIONS: 0
```

**0 violations over 20,439 elements, of which 5,965 are label elements.** Three things are
checked per label: its own `revealed_chapter <= n`, its node's reveal (both-rule), and that
the displayed name is itself one of the revealed labels — so a display name can never be a
string the fence has not released.

**Two negative controls, because the surface has two independent ways to leak:**

```
graph_node_label 1:SYNTHETIC LABEL CANARY: label 'SYNTHETIC LABEL CANARY' (epithet) on node 1 is revealed at 6
graph_node_label 51:Thessaly: label 'Thessaly' rides an unrevealed node 51 (both-rule)
...
DETECTOR VERIFIED TO FIRE: True
```

a late label on an early node (its own reveal must gate it) and an early label on a late
node (the node's reveal must gate it). Both fire. The controls also run against the
**frozen** database, which is the case most likely to have a gap, by creating the table on
the throwaway copy.

Display name at chapter n is the most recently revealed **naming** label (full/short/
epithet), ordered by reveal chapter desc, then primary, then kind, then length — so the
result is deterministic rather than insertion-ordered. **A title never becomes the display
name**: R3 task 5 says a title *attaches* to a person, so once "the Warden" links to Orin
Drask the node still reads "Orin Drask" and carries the title alongside.

One consequence worth flagging for R7: because recency wins, a **shortening** does take
over once it appears — a node reads "Warden-Captain Orin Drask" at ch1 and "Drask" from
ch3. That is what the spec asks for and it is what the reader most recently read, but it
makes the label change as the chapter slider moves. Candidate for R7 to revisit on
readability grounds; not changed unilaterally here.

## 4. Entity detection on the 4-type projected key — [MEASURED]

```
--- pooled over chapters 9, 17, 37 ---
  [strict] TP=24 FP=17 FN=14  P=0.5854 R=0.6316 F1=0.6076
      Character     TP=13  FP=7   FN=5   P=0.650 R=0.722 F1=0.684
      Item          TP=0   FP=4   FN=1   P=0.000 R=0.000 F1=0.000
      Organization  TP=2   FP=1   FN=5   P=0.667 R=0.286 F1=0.400
      Place         TP=9   FP=5   FN=3   P=0.643 R=0.750 F1=0.692
  [alias_aware] TP=26 FP=15 FN=12  P=0.6341 R=0.6842 F1=0.6582
```

Per chapter, strict: ch9 `TP=11 FP=7 FN=8 F1=0.5946` · ch17 `TP=7 FP=8 FN=5 F1=0.5185` ·
ch37 `TP=6 FP=2 FN=1 F1=0.8000` (alias-aware ch37: `F1=0.9333`).

Extraction counts on the full 40 chapters: **806 mentions → 188 entities** (Place 59,
Item 54, Character 53, Organization 22), 240 labels (200 `full`, 40 `short`).

Reading it honestly:

- **Type confusion is structurally gone**, which was the phase's purpose: every stored type
  is drawable, so a "type disagreement" error of the kind that produced 16 of v1's 44
  entity errors can no longer be expressed. That is a property of the design, not a score.
- **Item is the weak type: P=0.000 on 4 false positives and 1 miss.** Sample size is 5
  reference items pooled, so the figure is nearly meaningless as a rate, but the direction
  is clear and it is the type to look at next. `Organization` recall is also poor (0.286,
  5 misses of 7).
- The rejected-string emission rate improved to **4 of 49 (0.0816)** from v1's 6 of 49
  (0.1224) — the same 49 strings the reference says should not be entities, so this one IS
  comparable, and it is better because `Concept`/`Event` prompts are gone.
- **Nothing was added in the same phase.** I briefly added an `"object"` prompt for Item
  recall and then removed it before the measured run, so the prompt set is exactly v1's
  four-type subset and the difference is attributable to the type reduction alone.

## 5. Aliases — the number that matters for R4 — [MEASURED]

R4's validator must find **both** participants' labels inside a quote, so alias recall is
worth more here than usual, and this is where R3 moved most.

```
--- pooled --- TP=3 FP=0 FN=2  P=1.0000 R=0.6000 F1=0.7500
  over-merges  (v1 joined what the reference separates): 0
  under-merges (reference joined what v1 separates):    2
```

Per chapter: ch9 `P=1.0000 R=0.3333 F1=0.5000` (2 under-merges) · ch17 `F1=1.0000`
(**0 under-merges — v1's `'scribe'+'sorrel'` miss is fixed**) · ch37 `F1=1.0000`.

| | v1 | R3 |
| --- | ---: | ---: |
| alias precision | 1.0000 | **1.0000** |
| alias recall | 0.5000 | **0.6000** |
| alias F1 | 0.6667 | **0.7500** |
| **over-merges** | **0** | **0** |
| under-merges | 3 | **2** |

**Over-merges = 0. The stop condition is not tripped.** (The alias metric is scored over
surface strings both sides know and is not affected by the type projection, so this
comparison is like-for-like.)

### Every under-merge in the scored chapters, with why

Both remaining under-merges are the same pair of clusters:

| pair | reference | R3 | why not merged |
| --- | --- | --- | --- |
| `'captain'` + `'drask'` | both under `Orin Drask` | kept apart | two rules refuse it independently. **Rule 1:** the full form is `Warden-Captain Orin Drask`, whose tokens are `("warden-captain", "orin", "drask")` — `captain` is not a token at all, it is inside the hyphenated compound, so it is not a contiguous word-subsequence. **Rule 4:** `captain` is a bare role word in the generic set, and a bare role word matches half a cast |
| `'captain'` + `'orin drask'` | same two clusters | kept apart | the same refusal; the metric counts the pair twice |

**This is exactly the case title linking is meant to solve** — `Captain` is an office, not a
shortening — and it is not solved here, because the corpus contains no comma-bracketed
apposition connecting them (§6). Honest status: the alias mechanism is right to refuse it,
and the mechanism that should catch it found no evidence in this text.

### Every merge refusal over the whole 40 chapters (19), with why

| refused shortening | candidate host | rule |
| --- | --- | --- |
| `aldenreach` | `aldenreach orphan house` | 2: short form first (ch1 before ch20) |
| `archive` | `rebuilt archive` | 2 (ch29 before ch39) |
| `bone market` | `beneath the bone market` | 2 (ch3 before ch6) |
| `court` | `ashen court` | 2 (ch35 before ch36) |
| `kaelen` | `kaelen the unmaker` | 2 (ch19 before ch25) |
| `keep` | `aldenreach keep` | 2 (ch14 before ch35) |
| `letter` | `half-finished letter` | 2 (ch1 before ch32) |
| `marrow` | `marrow seal` | 2 (ch20 before ch24) |
| `ninth house` | `old ninth house` | 2 (ch1 before ch19) |
| `regency` | `regency council` | 2 (ch1 before ch2) |
| `regent` | `lord regent` | 2 (ch28 before ch35) |
| `salt tithe` | `salt tithe rolls` | 2 (ch2 before ch12) |
| `captain` | — | 4: bare role word |
| `child` | — | 4 |
| `girl` | — | 4 |
| `king` | — | 4 |
| `household` | `ashcombe household` / `regent's household` | ambiguous: 2 candidates |
| `quarter` | `across the quarter` / `salt quarter` | ambiguous: 2 candidates |
| `vell` | 5 candidates | ambiguous: `corwin vell`, `duchess meraude vell`, `s. vell`, `sable vell`, `tobin vell` |

Rule 2 is doing real work rather than blocking good merges: `marrow` is a **person's**
surname and `marrow seal` is an **item**; `the Ninth House` is not `old Ninth House`;
`regency` is not the `regency council`. The three ambiguous refusals are the over-merge
guard earning its place — `vell` is five different Vells.

### Two fixes the measurement forced

1. **The 6-chapter window was wrong for this book.** It refused 16 correct shortenings —
   `juno`→`juno stray`, `fennick`→`lord fennick oswald`, `ione`→`ione ashcombe`,
   `robart kell`→`ser robart kell`, `pryn`→`pryn voss`, `casimir`→`casimir lowe`,
   `mira`→`mira quell`, `corwin`→`corwin vell`, `pello`→`pello ashcombe`,
   `vane`→`master vane`, `ysolde fenn`→`maester ysolde fenn` and others — because the book
   names a character in full once, early, then uses the bare surname for the rest of the
   book, and over 40 chapters that gap routinely exceeds 6. Measured sweep:

   | window | clusters | merges | refused | of which rule 3 |
   | ---: | ---: | ---: | ---: | ---: |
   | 6 | 206 | 27 | 32 | 16 |
   | 10 | 204 | 29 | 30 | 12 |
   | 20 | 195 | 38 | 21 | 3 |
   | **40** | **192** | **41** | **18** | **0** |

   Set to 40 in `data/samples/the-ninth-house/storyweave.toml` — per-work DATA, with the
   reasoning in the file. It costs no safety: rules 1, 2, 4 and the ambiguity guard are all
   independent of the window, and over-merges stayed at 0.

2. **`'girl' → 'chancery girl'` was an over-merge waiting to happen.** Widening the window
   admitted it: a bare common noun folding into a character would fuse every unnamed girl
   in the book. Bare person-nouns and role words (`girl`, `boy`, `child`, `captain`,
   `master`, `maester`, `scribe`, …) joined the generic set, so rule 4 refuses them the way
   it already refused `man`/`woman`. Modified forms are untouched — `chancery girl` is
   still its own entity. This is why the final count is 40 merges, not 41.

### Rule 5, honestly

"The short form does not match another entity's full name" has **no separate check**, and a
check there could never fire: reps are keyed by normalized surface, so a short form spelled
like another entity's full name *is* that rep — there is one `drask`, not two. The failure
mode the rule describes ("could belong to more than one full name") is the same condition
as the ambiguity guard, and that is where it is enforced. The cross-type variant (`Vane`
the place vs `Sorrel Vane` the character) is excluded by rule 1's same-type requirement and
is tested. Written up rather than left as dead code that looks like a check.

## 6. Title linking: 0 links, and that is the correct answer — [MEASURED]

**Accepted: 0. Refused: 0.** The corpus contains no title apposition in the required form.
Verified independently of the implementation by grepping the 40 chapters for
`Name, the Title,` and `the Title, Name,` — **zero matches** for either. The only
`Name, the X` constructions in the whole book are descriptive noun phrases and possessives:

```
Marrow, the Ninth House's last acknowledged daughter
Undercroft, the chancery girl's true name
Vell, the Duchess's ...
```

The mechanism works — four unit tests cover it, including a linked title being invisible
at k−1 and visible at k (R3 task 7) — it simply has nothing to fire on here.

**It took two false positives to get to zero.** The first implementation produced exactly
two links and **both were wrong**:

| bogus link | why |
| --- | --- |
| ch20 `"the Ninth House's"` → `Aurelia Marrow` | the title pattern swallowed a **possessive**: "Aurelia Marrow, the Ninth House's last acknowledged daughter" is a description, not an office |
| ch21 `'the Chancery'` → `Ser Robart Kell` | "At the Chancery, Ser Robart Kell noticed …" is a **fronted prepositional phrase**, not an apposition at all |

Three guards were added in response, each aimed at a measured failure: no apostrophe in the
title word class; a title must end at an apposition boundary (`,` `.` `;` or ` of `), which
also stops a long noun phrase being truncated into a fake title like `"the Ninth"`; the
pre-posed pattern requires **both** commas; and a title preceded by a preposition is
rejected. After that, 0 accepted and 0 wrong.

Reported as a negative result rather than dressed up: **R3 ships title linking with zero
measured links on this corpus.** Its value is the mechanism plus the guards; if a later
corpus has appositions it will find them, and R4's validator can read the quote it stores.

## 7. Migration — [MEASURED]

`tools/migrate_entity_labels.py`, up and down, tested on a fixture database in
`test_migration_up_then_down`:

- **up** on a copy of the frozen baseline wrote **293 labels across 219 entities**. Each
  alias is stamped with the chapter that surface **first appears** in, not the entity's
  reveal chapter — backfilling from `nodes.revealed_chapter` would leak every alias to the
  entity's first chapter. Asserted directly: the alias is invisible at chapter 3 and visible
  at 4.
- **up** is idempotent (the `UNIQUE (entity_id, label, kind)` key absorbs a re-run).
- **down** drops the table and touches nothing else; node count unchanged.
- No node row is altered and no type is rewritten.

The migration is offered but **not required**: `has_entity_labels_table()` means an
unmigrated database still serves, falling back to `nodes.name`.

## 8. Gates and environment — [MEASURED]

| gate | result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `mypy` | `Success: no issues found in 85 source files` |
| `pytest` | `221 passed, 6 skipped` (185 before R3; 36 new) |
| `tools/check_local_env.py` | `PASS: all 10 checks are on the project drive.` (both venvs) |

C: sizes, against the R0 baseline in `R0_local_paths.md` — GLiNER ran twice in this phase:

| path | R0 | R3 |
| --- | ---: | ---: |
| `C:\Users\space\.cache` | 135.8 MB | **135.8 MB** (unchanged) |
| `C:\Users\space\AppData\Local\pip` | absent | **absent** |
| `C:\Users\space\.ollama` | absent | **absent** |
| `C:\Users\space\AppData\Local\ms-playwright` | absent | **absent** |
| `C:\Users\space\AppData\Local\Temp` | 92.3 MB | 93.1 MB (OS-shared; this project writes to `.local\tmp`) |

Nothing was downloaded: both GLiNER runs read from `F:\Dev\shared\hf-cache`.

## 9. Model availability for R4 — report only, nothing installed

| model | status | size on disk |
| --- | --- | ---: |
| `urchade/gliner_small-v2.1` (entities) | **present**, used this phase | 583 MB |
| `microsoft/deberta-v3-small` (its encoder) | **present** | — |
| `knowledgator/gliner-relex-base-v1.0` (Tier-2 relations) | **present and loads** | 870 MB |
| `sentence-transformers/all-MiniLM-L6-v2` (search embeddings) | **absent** | — |

All in `F:\Dev\shared\hf-cache`, off C:. Relex was constructed successfully with
`HF_HUB_OFFLINE=1` set, which proves R4 needs **no download**: `model.safetensors`,
`tokenizer.json`, `spm.model` and `gliner_config.json` are all on disk.

**What R4 needs that is not yet downloaded: nothing.** Reading R4's tasks — the 12-relation
table, the producer mapping from `nlp/relex.py` prompts, `storyweave/extract/validator.py`,
the weight/grade columns, and dropping the `nx.DiGraph` projection — the only model involved
is relex, which is present. The absent MiniLM embedding model is for vector *search*, which
R4 does not touch.

**R4 is fully Ollama-free, confirmed.** Ollama is not installed (`where ollama`: not found;
`C:\Users\space\.ollama` absent) and R4 never mentions it: its edges come from GLiNER-RelEx
plus the rule-based validator. The LLM tier is R5's, and R5 is explicitly optional — the
README's minimum viable path is R0 → R1 → R4 → R6 → R7, which excludes it. Nothing in R4
requires a local LLM, an API key, or any outbound call.

## 10. Stop conditions — none tripped

| stop condition | status |
| --- | --- |
| `tools/check_local_env.py` fails | passes, 10/10, both venvs |
| any fence violation | **0** over 20,439 elements (R3 DB) and **0** over 95,530 (frozen DB); label canaries fire |
| **any alias over-merge** | **0** — measured, and the guard that keeps it at 0 is tested |
| any SAME_AS false positive | none; R3 creates no identity edges |
| ch40 default graph < 10 or > 40 nodes | not applicable — no default-cast filter until R6 |
| R5 lowering precision | not applicable |

## 11. What R3 leaves for later

- **Item precision (P=0.000 on 5 pooled reference items)** is the worst remaining type and
  was not addressed; adding a recall prompt in this phase would have confounded the
  measurement.
- **`'captain'` ↔ `Orin Drask`** stays unmerged. The honest fix is a title/honorific label,
  which needs either an apposition the text does not contain or a looser pattern than R3
  permits.
- **Display-name churn**: a shortening takes over the label once it appears. Spec-correct,
  possibly bad for R7's readability goal.
- **`LabelKind.DESCRIPTION` is defined but never populated.** "Aurelia Marrow, the Ninth
  House's last acknowledged daughter" is a real descriptive apposition and would be a
  reasonable source for it; out of scope for a phase about titles.
