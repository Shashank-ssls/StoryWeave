> **v2 design document. The retrofit (tag `retrofit-v1.0`) implemented a subset. See [`docs/retrofit/design/IMPLEMENTED.md`](IMPLEMENTED.md).**

# StoryWeave v2 — Ontology and Extraction Policy

**Status:** Phase 0 specification. Frozen before any v2 code is written.
**Supersedes:** all v1 schema and extraction behaviour.
**Scope:** this document defines *what is extracted, what is stored, and what
is shown*. It does not define implementation, file layout, or API routes.

---

## 0. Why this document exists

v1 extracted every named thing and connected every co-mention. Measured result
at chapter 40 of *The Ninth House*: 206 nodes and 1316 edges served to the
client, with an edge density that made the graph unreadable to both a
graph-engineering reviewer and a non-technical reader.

The failure was not visual. It was policy: **everything mentioned became a
node, and everything co-mentioned became an edge.**

v2 replaces that with an explicit policy. An entity must *earn* a node. An edge
must *earn* a line. Every claim must carry its evidence.

### The four governing principles

1. **Enforcement at the data layer, not the view layer.** Filters are SQL
   `WHERE` clauses on the query that builds the payload. Nothing is filtered in
   the browser. v1's salience demotion was a client-side lowercase-label
   heuristic; v2 has no client-side filtering of any kind.
2. **Measured, not asserted.** Every claim in an artifact is labelled by
   evidence type. A correct outcome whose failure mode was never stressed is a
   weak zero and is documented as such.
3. **Citation or nothing.** Every relation, event, death and identity link
   carries a verbatim quote from the source text. No quote, no row.
4. **The model proposes, the code disposes.** An LLM never writes directly to
   the database. Its output is validated in code against a closed schema, and
   anything violating the schema is discarded.

---

## 1. Text preparation (Stage 0)

This stage runs before any extraction. It is mandatory. Skipping it means every
downstream measurement is measuring garbage.

### 1.1 Why it exists

Web-serial source text contains deliberate anti-scraping contamination.
Observed in real source material:

- Inline watermark tags: `<novelsnext> ... </novelsnext>`
- Domain watermarks using **Greek and Cyrillic homoglyphs**: `ndαsnοvεl.cοm`
  (the `α` and `ο` are not Latin `a` and `o`)
- Mid-sentence insertion, breaking sentence segmentation

Untreated, this causes: broken sentence splits, quote-verbatim checks failing on
valid relations, and watermark fragments entering the NER output as proper nouns.

### 1.2 Pipeline

| Step | Operation |
|---|---|
| 1 | Unicode NFKC normalisation |
| 2 | Homoglyph folding — Greek/Cyrillic look-alikes mapped to Latin |
| 3 | Watermark strip — known tag patterns, then a domain-like-token regex |
| 4 | Quote-mark normalisation — curly to straight |
| 5 | Whitespace and paragraph normalisation |
| 6 | Paragraph numbering — stable IDs assigned **after** cleaning |

### 1.3 Storage rule

Store **both** the raw text and the cleaned text. All quote spans, paragraph
IDs and character offsets index into the **cleaned** text.

Rationale: if quotes index into raw text, every improvement to the cleaner
invalidates every stored quote and every annotation reference.

### 1.4 Quotation marks carry meaning — do not normalise them away

Observed convention in serialized fiction:

| Mark | Meaning | Counts as interaction? |
|---|---|---|
| `" "` | Spoken aloud | **Yes** |
| `' '` | Internal monologue | **No** — one speaker, no interaction |
| `[ ]` | Mind-to-mind / telepathy | **Yes** |

The cleaner **must not** convert `'` into `"`, and **must not** strip square
brackets. Bracketed telepathy carries substantial relational content.

Internal monologue proves a character is present and thinking. It creates no
interaction and must not contribute to interaction-based signals.

---

## 2. Node types

Four types. Only these are ever drawn as shapes.

| Type | Default visibility | Definition |
|---|---|---|
| **Character** | **Always on** | A being with agency — human, monster, spirit, animal, or any non-human that acts or is acted upon as an individual |
| Organization | Overlay, off | A named group: house, order, council, guild, army, sect |
| Place | Overlay, off | A named location: city, building, region, realm |
| Item | Overlay, off | A specific physical object of narrative consequence |

### 2.1 Character-only by default

The default graph shows **Characters only**. Organization, Place and Item are
overlay toggles, off by default.

Rationale: node-type heterogeneity was the primary driver of visual density.
Every narrative has people and ties between them; which *other* types matter is
genre-dependent. A romance has no meaningful items; a cultivation novel does. An
ontology that hard-codes four equal types is right for the book it was designed
on and wrong elsewhere. Making the graph mono-typed by default, with optional
heterogeneous overlays, lets the reader choose their own complexity.

### 2.2 Removed from the graph

| Removed type | New home |
|---|---|
| Event | Timeline page — still a real database table (§8) |
| Ability | Field on the character card |
| Title | `entity_labels` as an alias (§5) — a title is a way of referring to a person, not a thing |
| Concept | Glossary (v3) or character card field |

### 2.3 Attributes, not types

- `species` is an attribute on Character. Kept — needed to distinguish human,
  monster and non-human agents.
- `rank` is **dropped**. If an author bothered to name something, the name
  carries the weight; `entity_labels` handles it better than a rank field.

---

## 3. The significance gate

An entity is stored regardless. An entity **earns a node** only by passing this
gate. Nothing is deleted; unqualified entities live in `mentions` and remain
searchable.

### 3.1 Standard path

An entity passes if **all** hold:

1. It has a **proper name**, not a role word (`mother`, `the boy`, `a scribe`)
2. It appears in **≥ 3 separate chapters**, or has **≥ 5 mentions** overall
3. It has **≥ 2 surviving edges** after edge filtering

### 3.2 Unnamed-but-important path

Some plot-central entities are never named. Observed: a character referred to
across a chapter only as *"a certain person"*, *"that person"*, *"that guy"*,
*"that abomination"* — five or more references, plot-critical, zero proper nouns.

An entity also passes if **all** hold:

1. A **stable definite description** used **≥ 3 times across ≥ 2 chapters**
2. It is the **subject or object of a verb** — it acts or is acted upon, rather
   than merely being mentioned
3. It has **≥ 1 surviving edge**

These carry `label_kind: description` and render in italics, so a reader can see
it is an unnamed referent. When a proper name eventually appears,
`entity_labels` picks it up and the node renames itself (§5.4).

### 3.3 Overlay types

Organization, Place and Item are subject to the same gate. `the heron ring` is a
plot item; `tax rolls` and `an empty room` are not.

---

## 4. Entity fields

| Field | Type | Notes |
|---|---|---|
| `id` | int | |
| `primary_name` | text | Display name — derived from `entity_labels` (§5) |
| `type` | enum | Character / Organization / Place / Item |
| `species` | text, null | Character only |
| `first_seen_chapter` | int | First appearance under **any** label |
| `named_chapter` | int, null | First called by its true name |
| `revealed_chapter` | int | **The fence reads this** (§10) |
| `salience_score` | real | 0–1 |
| `salience_rank` | int | 1..N — **filters use rank, not score** (§11) |
| `died_chapter` | int, null | When death occurred |
| `death_revealed_ch` | int, null | **The fence reads this, not `died_chapter`** |
| `death_grade` | enum, null | STATED / INFERRED |
| `death_quote` | text, null | |

These are **columns on a node**, never nodes themselves. They decide *whether* a
node is drawn and *how* it looks. They are never rendered as shapes.

---

## 5. Entity labels

One entity, many names, each with the chapter the reader learns it.

```sql
CREATE TABLE entity_labels (
  entity_id         INTEGER NOT NULL,
  label             TEXT    NOT NULL,
  kind              TEXT    NOT NULL,  -- see 5.1
  revealed_chapter  INTEGER NOT NULL,
  is_primary        BOOLEAN NOT NULL,
  quote             TEXT    NOT NULL
);
```

### 5.1 Label kinds

| kind | Example |
|---|---|
| `full` | "Anvil of Valor", "Ser Robart Kell" |
| `short` | "Anvil", "Valor", "Kell" |
| `title` | "the Warden", "the Regent" |
| `epithet` | "the Kingslayer" |
| `description` | "the thing in the well", "the hooded man" |

### 5.2 Display rule

The node shows the **most recent label the reader has earned**:

```sql
SELECT label FROM entity_labels
WHERE entity_id = :id AND revealed_chapter <= :n
ORDER BY revealed_chapter DESC LIMIT 1;
```

### 5.3 Abbreviation merge rule

A candidate merges into an existing entity only if **all** hold:

1. It is a **contiguous word-subsequence** of the full name — "Anvil", "Valor"
   and "Anvil of Valor" qualify; "Val" and "the Anvil's Valor" do not
2. Both appear in the **same chapter or within a small window**
3. The full form appeared **first**, or in the same chapter
4. The short form does **not** already match a different known entity's full name
5. It is not a stop-word-only fragment — "of", "the", "House"

**Rule 4 is load-bearing.** If a book has a character named Valor *and* an item
called Anvil of Valor, rule 4 blocks the merge and they stay separate.

**When ambiguous, do not merge.** A false merge destroys a distinction the
reader can see. A false split adds a node. Splits are recoverable; merges are not.

### 5.4 Titles and late naming

Titles are chapter-gated aliases:

```
entity 12 (Thessaly):
  "Thessaly"     revealed_chapter: 14   is_primary: true    kind: name
  "the Warden"   revealed_chapter: 19   is_primary: false   kind: title
```

The title becomes linkable to the person only at the chapter where the text
**connects** them. A reader at chapter 16 reading "the Warden" does not know who
that is, so before chapter 19 "the Warden" remains a separate, unlinked entity.

Linking a title to a name early is a spoiler. This is a fence surface.

Same mechanism handles late-named entities:

```
entity 47:
  "the thing in the well"   revealed_chapter: 3    kind: description
  "the Well-Thing"          revealed_chapter: 8    kind: description
  "Gravewyrm"               revealed_chapter: 19   kind: full, is_primary
```

The node exists from chapter 3 — the reader knew something was in the well. Its
*name* changes at 19.

---

## 6. Relations

Twelve. Two rings.

### Ring 1 — default graph

| Relation | Direction | Can end | Extra fields |
|---|---|---|---|
| `KIN_OF` | A → B | No | `kin_role`, `surface_term` |
| `ROMANTIC_WITH` | symmetric | Yes | |
| `ALLY_OF` | symmetric | Yes | |
| `ENEMY_OF` | symmetric | Yes | |
| `SERVES` | A → B | Yes | |
| `MENTOR_OF` | A → B | Yes | |
| `KILLED` | A → B | No | |
| `SAME_AS` | symmetric | No | |

### Ring 2 — overlays only

| Relation | Direction | Can end |
|---|---|---|
| `MEMBER_OF` | A → B | Yes |
| `LEADS` | A → B | Yes |
| `OWNS` | A → B | Yes |
| `LOCATED_IN` | A → B | Yes |

Turning on the Organization overlay activates `MEMBER_OF` and `LEADS`; Item
activates `OWNS`; Place activates `LOCATED_IN`.

### 6.1 Deliberately excluded

| Excluded | Why |
|---|---|
| `TALKS_TO`, `MEETS`, `APPEARS_WITH` | Co-occurrence in disguise. This is the hairball. Dialogue is used as a *signal* feeding salience and edge weight, never as its own edge type. |
| `BETRAYS` | An event, not a standing state |
| `PARENT_OF`, `SIBLING_OF`, `SPOUSE_OF` | Collapse into `KIN_OF` with `kin_role`. Six extra relations would halve the per-type sample size. |

**Boundary rule:** relations are states that persist; events are things that
happen at a chapter. If you cannot say *"X is currently Y's ___"*, it is an event.

### 6.2 `KIN_OF` — directed

```
KIN_OF(head, tail, kin_role, surface_term)
  reads as:  head is the tail's <kin_role>
```

Store each kinship fact **once**, in the direction the text states it. Never
write the reverse edge.

| `kin_role` | Inverse (derived in code, never stored) |
|---|---|
| `parent` | `child` |
| `child` | `parent` |
| `sibling` | `sibling` |
| `spouse` | `spouse` |
| `grandparent` | `grandchild` |
| `grandchild` | `grandparent` |
| `pibling` (aunt/uncle) | `nibling` |
| `nibling` (niece/nephew) | `pibling` |
| `cousin` | `cousin` |
| `other` | `other` |

`surface_term` holds the exact kinship word from the quote — "father", "sister",
"sire", "half-brother".

**Display:** forward reading shows `surface_term`; backward reading shows the
neutral inverse. Never show `surface_term` on the reverse — storing "father" and
rendering the reverse as "father" asserts the child is the parent's father.
Gendered inverse derivation ("daughter") requires gender inference and is v3.

### 6.3 `KIN_OF` — the metaphor guard

Kinship words are among the most metaphorically abused words in fiction. Sworn
comrades say "brother". Religious orders say "sister". Mentors are called
"father". Sarcasm uses all of them.

Observed real case: a character says *"Am I not blessed to suddenly get such a
wonderful little sister?"* to an unrelated person. A naive extractor produces a
`KIN_OF` edge with a perfect STATED quote, and it is wrong.

**A `KIN_OF` edge requires one of:**

1. A **possessive genitive construction** — "Sorrel's father", "his niece",
   "her brother" — where the kin word attaches grammatically to the other party
2. **Corroboration** — the same kin claim appears in **≥ 2 separate chapters**

A vocative (*"my sister"*, *"sister!"*) or a dialogue predicate (*"you are like
a sister to me"*) is **not sufficient on its own**.

Check: *"The Saint looked at his niece"* → genitive, passes. *"such a wonderful
little sister"* → vocative in dialogue, blocked.

### 6.4 `SAME_AS` versus alias

The operational test:

> **Before this chapter, did the reader encounter both labels as what appeared
> to be two separate beings?**

| Answer | Verdict |
|---|---|
| Yes — separate, now revealed as one | `SAME_AS` |
| No — the second label arrived already attached | Alias in `entity_labels` |

Implementation: `SAME_AS` requires that **both labels have independent mention
history before the linking chapter**. If one label has no prior standalone
mentions, it is an alias. This is checkable in SQL, not a judgement call.

Examples:
- "Whispering Blade" and "Madoc" used interchangeably in the same chapter, never
  presented as separate beings → **alias**
- "the Wanderer" appearing for twenty chapters, then revealed to be Vesper →
  **`SAME_AS`**

`SAME_AS` is the project's most novel contribution and has the highest cost of
error: a false positive is a spoiler or a false plot claim. **Precision must be
~1.0; recall may be low.** The citation gate is never relaxed.

### 6.5 Directional labels

One lookup table. Every edge label comes from here.

| Relation | Forward | Backward |
|---|---|---|
| `KIN_OF` | `surface_term` | neutral inverse |
| `MENTOR_OF` | teaches | trained by |
| `SERVES` | serves | commands |
| `KILLED` | killed | killed by |
| `MEMBER_OF` | member of | has member |
| `LEADS` | leads | led by |
| `OWNS` | owns | owned by |
| `LOCATED_IN` | in | contains |

`ROMANTIC_WITH`, `ALLY_OF`, `ENEMY_OF` and `SAME_AS` read the same both ways.

### 6.6 Label display by view

| View | Edge labels |
|---|---|
| Full graph | None. Arrowheads only. Label on hover. |
| Ego graph (1 hop, ~12 nodes) | On |
| Dossier | Always, as a list — *"King Aldric · father · ch. I"* |

---

## 7. Domain/range validator

C = Character, O = Organization, P = Place, I = Item.

| Relation | Head may be | Tail may be | Symmetric |
|---|---|---|---|
| `KIN_OF` | C | C | ✗ |
| `ROMANTIC_WITH` | C | C | ✓ |
| `ALLY_OF` | C, O | C, O | ✓ |
| `ENEMY_OF` | C, O | C, O | ✓ |
| `SERVES` | C | C, O | ✗ |
| `MENTOR_OF` | C | C | ✗ |
| `KILLED` | C | C | ✗ |
| `SAME_AS` | C | C | ✓ |
| `MEMBER_OF` | C | O | ✗ |
| `LEADS` | C | O, P | ✗ |
| `OWNS` | C, O | I | ✗ |
| `LOCATED_IN` | C, O, P | P | ✗ |

**Anything violating this table is rejected in code before it reaches the
database.** `LEADS(tax rolls, outer hall)` has an Item head and a Place tail →
rejected. This is the v1 `Ascent-related paperwork` failure, killed by a lookup.

Monsters and non-human agents are Characters with a `species` attribute, so
`KILLED(C, C)` covers them without a fifth node type.

---

## 8. Edge fields

| Field | Notes |
|---|---|
| `relation` | Enum, the twelve of §6 |
| `head_id`, `tail_id` | |
| `valid_from_chapter` | When it became true, proven by quote |
| `valid_to_chapter` | NULL = still true. **v2 sets this via death cascade only** (§9.3) |
| `revealed_chapter` | **The fence reads this** |
| `grade` | STATED / INFERRED |
| `quote` | Must exist verbatim in the cleaned text |
| `quote_chapter` | |
| `weight` | Times confirmed — feeds the backbone filter |
| `kin_role` | `KIN_OF` only |
| `surface_term` | `KIN_OF` only |

### 8.1 Weight, not duplicates

If two entities are connected in chapters 1, 7, 14 and 22, that is **one edge
with weight 4**, not four edges.

This also fixes a measured v1 defect: v1's `build_graph` projected into
`nx.DiGraph`, which cannot hold parallel edges, so same-direction duplicates
were silently dropped between the database and the client (1326 fenced rows
served as 1316 at chapter 40), and in one case an identity edge was relabelled by
the collapse. With `weight`, there are no parallel edges to collapse. The defect
disappears by design rather than by patch.

### 8.2 Three chapter numbers

`valid_from_chapter`, `valid_to_chapter` and `revealed_chapter` mean different
things. This is the subtlest part of the schema and the most likely source of
spoiler leaks. See §10.

---

## 9. Death

Death is not one relation among twelve. It is the most frequent consequential
event in serialized fiction, it uses a very large verb vocabulary, and it changes
the whole graph. It is treated as a subsystem.

### 9.1 Status on the entity

`died_chapter`, `death_revealed_ch`, `death_grade`, `death_quote` (§4).

A character may die in chapter 22 but the reader only learn it in chapter 27.
**The fence reads `death_revealed_ch`, never `died_chapter`.** Getting this
backwards shows a character as dead before the reader is told. This requires a
specific test case.

### 9.2 Event and relation

A death always produces a `death` event (§10) *and* sets the entity status.

A `KILLED` edge is produced **only if the text names the killer**. If the text
says "Kell was found dead", record the death with no `KILLED` edge. **Never infer
a killer.**

### 9.3 Cascade

```
When died_chapter is set for entity X:
    for every edge touching X whose relation can end:
        if valid_to_chapter IS NULL:
            valid_to_chapter = died_chapter
```

Closable: `SERVES`, `ALLY_OF`, `ROMANTIC_WITH`, `MEMBER_OF`, `LOCATED_IN`.
Not closable: `KIN_OF`, `KILLED` — you remain someone's brother after death.

This gives most of the benefit of relationship-endings for almost no extra
extraction work.

### 9.4 Verb lexicon

Roughly 60–80 verbs in seven groups, used as a **fast candidate filter**:

- *direct violence* — kill, slay, slaughter, murder, butcher, behead, stab,
  strangle, cut down, put to the sword
- *battle* — fall, perish, be felled, be struck down, die in battle
- *execution* — execute, hang, burn, behead (formal)
- *attrition* — starve, freeze, succumb, waste away, bleed out
- *consumption (non-human)* — devour, consume, absorb, annihilate, obliterate
- *mass* — wipe out, massacre, exterminate, raze
- *euphemism* — pass, fall silent, be no more, breathe their last

The lexicon alone is insufficient. GLiNER is zero-shot, so a `"death event"`
label is run as a **recall net** over the same text. Both passes feed candidates
to the LLM stage.

### 9.5 Rendering

A dead node renders differently — outlined rather than filled. A reader at
chapter 30 sees Kell dimmed; a reader at chapter 15 sees him normal. This is the
fence doing visible, legible work.

### 9.6 Resurrection

`died_chapter` is **overwritable by a later STATED event**. If chapter 30 says
"she stood, alive", `died_chapter` is cleared and a `transformation` event is
recorded. No full life-state timeline in v2; the schema simply must not treat
death as permanent.

---

## 10. Events

Events are a **first-class deliverable in v2**, not a by-product of the graph.
The timeline is the primary reading surface; the graph is a relationship lens.

### 10.1 Kinds

Ten. Closed list.

| Kind | Covers | Attribute |
|---|---|---|
| `death` | Dies, killed, destroyed, consumed | — |
| `reveal` | A hidden identity or secret **about a person** becomes known | — |
| `betrayal` | Trust broken, side switched, informed on | — |
| `pact` | Alliance, oath, contract, marriage | `formed` / `broken` |
| `conflict` | Battle, duel, ambush, siege, fight | — |
| `movement` | Arrives, departs, exiled, imprisoned, escapes | `arrival` / `departure` |
| `gain` | Acquires item, power, rank, title, territory | — |
| `loss` | Loses item, power, rank, status — **not** death | — |
| `discovery` | Finds a place, object, or fact **about the world** | — |
| `transformation` | Awakening, curse, ascension, resurrection | — |

Design notes: `pact` merges alliance and oath, and its `broken` attribute yields
alliance endings for free. `movement` merges arrival and departure. `gain` exists
because progression fiction's main event type had no home. `reveal` (a person's
secret) and `discovery` (a fact about the world) are cleanly separated.

**This list is what v2 attempts, not what v2 ships.** Per-kind F1 is measured,
and kinds that score poorly are excluded from the default timeline and reported
as measured negatives.

### 10.2 Schema

```sql
CREATE TABLE events (
  id                INTEGER PRIMARY KEY,
  work_id           INTEGER NOT NULL,
  chapter           INTEGER NOT NULL,   -- where it happened
  revealed_chapter  INTEGER NOT NULL,   -- fence
  kind              TEXT    NOT NULL,   -- closed list above
  attribute         TEXT,               -- formed/broken, arrival/departure
  summary           TEXT    NOT NULL,   -- one plain line
  quote             TEXT    NOT NULL,   -- verbatim span
  grade             TEXT    NOT NULL,   -- STATED / INFERRED
  salience          REAL    NOT NULL,   -- for "major beats only"
  place_id          INTEGER
);

CREATE TABLE event_participants (
  event_id   INTEGER NOT NULL,
  entity_id  INTEGER NOT NULL,
  role       TEXT    NOT NULL   -- actor | target | witness | mentioned
);
```

### 10.3 Grading events

Events are the highest-volume, lowest-precision extraction target, and an
inferred event on a spoiler-aware timeline is worse than no event.

**STATED** requires the quote to contain the resolved participant names **and**
the action verb. The quote alone must prove the claim to someone who has read
nothing else.

Counter-example that must be graded INFERRED:

```
summary: "Thessaly hands the Ninth House ledgers to Vesper."
quote:   "She set the ledgers down without looking at him."
```

The quote names nobody. Who, what, and the significance were all supplied by the
model. On a novel nobody has read, there is no way to tell understanding from
hallucination.

**v2 default: STATED only.** The INFERRED path is not built in v2. Grades are
scored separately in evaluation.

### 10.4 Extraction with a verifier

```
1. Find sentences containing ≥1 resolved entity AND a verb from the
   event-verb list
2. Send only those sentences, plus two sentences of context, to the LLM
3. The LLM must return: kind (closed list), participants, quote span
4. CODE VERIFIES — not the LLM:
     quote span exists verbatim in the cleaned text?   else reject
     kind in the allowed list?                          else reject
     every participant exists as an entity?             else reject
     participant names appear inside the quote?         STATED if yes
     participant types match the kind's allowed roles?  else reject
5. Store with grade and provenance
```

---

## 11. The `revealed_chapter` invariant

**One rule, applied to every table:**

> `revealed_chapter` = the chapter of the quote that proves the fact. Never
> earlier. Where several quotes prove it, the earliest qualifying one.

| Table | `revealed_chapter` is |
|---|---|
| `entities` | Chapter of first mention under any label |
| `entity_labels` | Chapter where this label is first used, or first linked |
| `edges` | Chapter of the proving quote |
| `events` | Chapter of the proving quote |
| Death | Chapter where the death is **stated**, not where it occurred |

The death row is the trap. Dies chapter 22, reader told chapter 27 →
`died_chapter = 22`, `death_revealed_ch = 27`. The fence reads 27.

### 11.1 Fence surfaces

v1 had one leak surface. v2 has six. Each needs its own test:

entities · edges · events · death status · identity links (`SAME_AS`) ·
label reveals (`entity_labels`)

---

## 12. Evidence grading

| Grade | Rule | Default visibility |
|---|---|---|
| **STATED** | The quote contains the participant names (or an alias used in that same quote) **and** the relation or action word | Shown |
| **INFERRED** | Anything requiring coreference resolution or cross-sentence assembly | Not built in v2; v3 behind a toggle |

Applies to relations, events, deaths and identity links. Graded separately in
evaluation. When in doubt, INFERRED.

---

## 13. Coreference

### 13.1 Scope — off the critical path

v2 ships STATED-only. A STATED relation requires both participants named in the
quote, so there is no pronoun to resolve. Coreference is therefore **not needed
for the default product**.

| Purpose | Needs coreference? |
|---|---|
| STATED relations, events, deaths | **No** |
| Salience mention counts | Yes, approximately |
| INFERRED relations | Yes — v3 |

This deliberately places the pipeline's weakest component where its failure
cannot damage the default output.

### 13.2 Method

`fastcoref` (Otmazgin et al., 2022), run **per chapter**, not whole-book.

**Hard filter:** accept a coreference cluster only if it contains at least one
proper-name mention. Discard all-pronoun clusters entirely.

Precision over recall throughout. Published work on literary character networks
found that high-recall, lower-precision coreference produces many spurious
co-occurrences that actively harm the analysis — being greedy makes the graph
worse, not merely bigger.

Resolved mentions feed salience counts. They **never** create a STATED relation.

---

## 14. Salience

### 14.1 Features

Computed **once after extraction**, stored as a column.

| Feature | Signal |
|---|---|
| Lifetime mention count | Overall prominence |
| **Recent mention count** | Mentions in the last ~10% of chapters read |
| Chapter spread | Present across 12 chapters beats 30 mentions in one |
| Has a proper name | |
| Speaks dialogue | `" "` and `[ ]`, **not** `' '` (§1.4) |
| Is the subject of verbs | Acts, rather than is mentioned |
| Graph centrality | Connects to other high-salience entities |

### 14.2 Combination

Each feature normalised to 0–1, **equal weights**, summed, then ranked.

Hand-tune once against the annotation, write the final weights into this
document, and do not change them again. **Do not learn the weights** — three
annotated chapters is far too little data, and a learned weighting that cannot be
explained is worse in a viva than a simple one that can.

**Do not ask an LLM whether a character is important.** Published work found LLMs
achieve high recall but poor precision on salience, labelling nearly every entity
as salient.

Compute salience **per book, not per chapter** — seeing all instances of an
entity across the document substantially improves salience accuracy.

### 14.3 Recency

Recency matters at long lengths. On a 1000+ chapter serial, lifetime mention
count alone puts characters from the first 300 chapters in the top 20 — some long
dead, most irrelevant to the current arc.

Lifetime and recent counts both feed the score. A character central 800 chapters
ago and absent since drops out of the principal cast but remains findable.

### 14.4 Rank, not threshold

Filters use `salience_rank`, never `salience_score`.

A score threshold behaves differently on a 20-chapter novel and a 200-chapter
one and would need retuning per book. Rank is universal — "top 20" means the same
thing everywhere.

### 14.5 Cast dial

| Setting | `cast_size` |
|---|---|
| **Principal** (default) | 20 |
| Extended | 50 |
| Everyone | ∞ |

Measured v1 finding for contrast: v1's principal filter is a **no-op** — the
rendered view and the everyone view are identical at every chapter, and its
206→157 reduction came entirely from node-type drops. v2's cast dial is a real
server-side rank cutoff.

---

## 15. Backbone extraction

### 15.1 Method

Disparity filter (Serrano et al., 2009), computed on edge `weight`.

Why not a simple weight threshold: a global cutoff erases minor characters
entirely, because *all* their edges are weak. The disparity filter judges each
edge **relative to its own node's other connections**, so a minor character keeps
their one important tie. It preserves nearly all scales, where a global threshold
by definition cuts off everything below a fixed value.

### 15.2 Per-chapter precomputation

```sql
CREATE TABLE edge_significance (
  edge_id  INTEGER NOT NULL,
  chapter  INTEGER NOT NULL,
  alpha    REAL    NOT NULL
);
```

Run the filter once per chapter at ingest, on the graph as it stands at that
chapter. Milliseconds each.

**Per-chapter is not an optimisation, it is correctness.** The filter judges an
edge against its node's other edges. At chapter 10 a node has 3 edges; at chapter
40 it has 20. The same edge is significant in one and noise in the other.
Computing once on the full graph would be wrong in precisely the way this project
exists to avoid.

Metric/distance backbone comparison is v3.

---

## 16. Query layer

Four filters, one query, all SQL.

| Order | Filter | Kind |
|---|---|---|
| 1 | `revealed_chapter <= :n` | **Safety** — the spoiler fence |
| 2 | `salience_rank <= :cast_size` | Display |
| 3 | `alpha <= :density` | Display |
| 4 | `grade = 'STATED'` unless toggled | Display |

```sql
WHERE e.revealed_chapter  <= :n            -- fence
  AND s.chapter            = :n
  AND s.alpha             <= :density      -- backbone
  AND ent.salience_rank   <= :cast_size    -- salience
  AND e.grade              = :grade_filter
```

The fence is a **safety** filter; the other three are **display** filters.
Keep them visibly separate in the code — the distinction is the thesis.

**No client-side filtering of any kind.** Everything the client receives is
everything the client may see.

---

## 17. Extraction pipeline

```
 0. Text normalisation (Stage 0)          §1
 1. Sentence split + candidate filter     GLiNER ONNX int8
 2. Character name clustering             "Tom" / "Mr. Sawyer" → one entity
 3. Coreference, precision-first          fastcoref, per chapter        §13
 4. Death pass                            lexicon + GLiNER recall net   §9.4
 5. Relation extraction on candidates     LLM, closed vocabulary        §6
 6. Schema validation in code             reject illegal triples        §7
 7. Store everything                      entities + mentions + edges + events
──────────────────────── query time ────────────────────────
 8. Salience scoring                      §14
 9. Backbone filter                       §15
10. Spoiler fence                         §11
```

Steps 0, 2, 4, 6, 8 and 9 are new in v2.

### 17.1 Model backends

| Component | Default | Notes |
|---|---|---|
| NER | GLiNER, ONNX int8 | Drops the torch dependency; parity-checked against torch |
| Coreference | fastcoref | |
| Relation / event extraction | Local Ollama | ₹0, offline, no API key |
| Optional backend | OpenRouter | One config flag. **Never the default** — the demo must run with no internet. |

Model cache is read from `HF_HOME`, falling back to `F:\Dev\shared\hf-cache`.
**Never write model weights into the repo.** v1 hardcoded a repo-local cache
path; v2 must not.

### 17.2 Empty results

Zero extractions from a chapter is a **valid result**. Log a warning, continue.
Never error, never silently retry.

---

## 18. Frontend

| View | Role |
|---|---|
| **Timeline** | **Primary surface.** Per-character rows, grouped by chapter, filterable by kind and salience. |
| **Cast page** | Landing page. Character cards for the principal cast. |
| Dossier | Per-entity detail — ties as a list, timeline, labels. Carried forward from v1; this page already worked. |
| Ego graph | 1 hop, ~12 nodes, edge labels on |
| Full graph | **Advanced view.** Not the front door. |
| Chapter slider | Unchanged |
| Cast dial | Principal / Extended / Everyone |
| Overlay toggles | Organization / Place / Item |

The graph stops being the product and becomes one lens on it. v1's first-contact
failure — a reviewer opening the app and understanding nothing — was a
consequence of the graph being the landing page.

---

## 19. Out of scope for v2

Listed as future work, not as failures. Each entry names a specific technical
direction.

| Item | Note |
|---|---|
| Dialogue attribution | Published systems report ~0.61–0.78 accuracy; a research problem inside the research problem |
| INFERRED extraction path | Requires the coreference quality v2 deliberately does not depend on |
| Full relationship endings | v2 closes edges via death cascade only; textual endings are harder than textual assertions |
| LitBank benchmarking | Schema mapping cost exceeds the value for a domain-specific system |
| Metric/distance backbone comparison | Ship the disparity filter; compare later |
| Gendered kin inverses | Needs gender inference |
| OpenRouter backend | Config stub only in v2 |
| Glossary page | Key terms fold into dossier cards |
| Desktop packaging | Depends on the ONNX work landing first |
| Full-length serial processing | v2 measures 40-chapter windows |

---

## 20. Validation corpus

| Work | Role | Chapters |
|---|---|---|
| *The Ninth House* | Primary. Translated-register serial. | 1–40 |
| *Shadow Slave* | **Universality guard.** Native-English serial, different register, different conventions. | 1–40 |

Both measured on a 40-chapter window. State explicitly in any report:
*"Validated on 40-chapter windows. Full-length processing of long-running serials
is not attempted and is future work."*

Chapter 1101 of *Shadow Slave* is retained as a **hard-case spot check** — it
contains scraper watermarks with homoglyphs, metaphorical kinship, three
quotation conventions, and an important unnamed entity. It is not part of any
measured run.

---

## 21. Open items

Resolved in `EVALUATION_PLAN.md`, not here:

- Final salience feature weights, after hand-tuning against the annotation
- Which event kinds survive the per-kind F1 cut
- Disparity filter alpha, tuned per work or fixed

---

## Appendix A — decision log

| Decision | Rationale |
|---|---|
| Four node types, Character-only default | Node-type heterogeneity drove density; other types are genre-dependent |
| Twelve relations, closed | Open vocabulary produced "Ascent-related paperwork" as a relation partner |
| No co-occurrence edges | Co-mention is not a relationship; this was the hairball's main source |
| `KIN_OF` directed | "parent" is meaningless without knowing whose |
| Death as a subsystem | Most frequent consequential event; changes the whole graph |
| Store everything, filter at query time | Re-extraction is slow; filter tuning must be instant; before/after numbers require both |
| Rank, not threshold | Universal across novel lengths |
| Per-chapter backbone | Edge significance is relative to a node's degree, which changes with chapter |
| STATED-only in v2 | Removes coreference from the critical path |
| Timeline primary, graph secondary | A node-link graph is good at topology and bad at sequence |
| Fresh repo, v1 archived | v1 is the measured "before"; its database is frozen and pushed |

---

*End of specification. Changes to this document require a corresponding change
to `EVALUATION_PLAN.md` and, if extraction behaviour changes, re-annotation.*
