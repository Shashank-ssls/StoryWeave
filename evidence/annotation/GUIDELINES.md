# Reference annotation guidelines — StoryWeave v1

These guidelines describe **the schema v1 actually emits**, so that phase 2 scores v1
against v1's own ontology. Everything below was read at generation time from
`storyweave/db/models.py`, `storyweave/nlp/labels.py`, `storyweave/graph/builder.py`
and the populated database (`the-ninth-house`). Nothing here is aspirational: if a relation
type exists in the schema but v1 never produced it for this work, that is stated.

## Chapters to annotate

- **Chapter 9** (early — introduces several entities): 15 entities are first revealed here (106 new edges), the most of any chapter in the first third excluding ch1.
- **Chapter 17** (middle — dense with established relations): 27 of its 43 newly revealed edges connect entities that were ALREADY revealed before this chapter — the highest such count in the middle third.
- **Chapter 37** (late — identity reveal / death): carries an identity reveal. All Tier-3/Killed edges in the work: ch5:ALIAS, ch10:SECRET_IDENTITY, ch16:ALIAS, ch20:SECRET_IDENTITY, ch28:REINCARNATION, ch34:REINCARNATION, ch37:TRANSMIGRATED_INTO. Chosen the latest one in the final third.

For each chapter you are given `ch<NN>_text.txt` (the exact `clean_text` the pipeline
saw, paragraphs numbered `[1]`, `[2]`, ...) and `ch<NN>_template.json`. Fill the
template. Refer to text positions by paragraph number.

## 1. Entities

v1 has exactly **eight** node types. There are no others; an annotation using any other
type cannot be scored.

| node type | count in this work |
| --- | ---: |
| `Place` | 55 |
| `Character` | 53 |
| `Item` | 28 |
| `Event` | 22 |
| `Concept` | 21 |
| `Organization` | 16 |
| `Title` | 6 |
| `Ability` | 5 |

The count column is how many canonical entities of that type v1 currently holds for the
whole work — context for what v1 tends to produce, not a target.

Type boundaries as v1 draws them (from `storyweave/nlp/labels.py`, which is the literal
zero-shot prompt list GLiNER is given):

- prompt `Character` -> `Character`
- prompt `person` -> `Character`
- prompt `Place` -> `Place`
- prompt `location` -> `Place`
- prompt `Organization` -> `Organization`
- prompt `faction` -> `Organization`
- prompt `Item` -> `Item`
- prompt `Ability` -> `Ability`
- prompt `Concept` -> `Concept`
- prompt `power system` -> `Concept`
- prompt `phenomenon` -> `Concept`
- prompt `language` -> `Concept`
- prompt `Event` -> `Event`
- prompt `Title` -> `Title`

So `Concept` deliberately covers **common-noun** ideas — power systems, languages, named
phenomena — not only proper nouns. `Title` is an honorific or office ("the Regent" as a
title), distinct from the `Character` who holds it. Species and Rank are `Concept`
subtypes, never node types of their own.

**Subtypes are optional and v1 does not populate them for this work**: every node here
has `subtype = NULL` (206 of 206). Leave `subtype` empty
unless you are confident; it will not be scored against a populated field.

Each entity object should carry:

```json
{"name": "", "type": "", "subtype": null, "first_paragraph": 0,
  "surface_forms": [], "notes": ""}
```

`name` is the canonical name you would expect the system to settle on. `surface_forms`
lists every distinct string in THIS chapter that refers to it.

## 2. Aliases

An alias record says two surface strings denote the same entity. Record it whenever the
chapter uses more than one name for one referent (epithets, titles used as names,
shortened forms, "the girl" used as a stable referent).

```json
{"canonical": "", "alias": "", "first_paragraph": 0,
  "kind": "shortening|epithet|title|pronoun-stable|other"}
```

This is separate from the Tier-3 `ALIAS` **relation** below, which is a reveal-bearing
claim about two entities the reader thought were different. A merely shortened name is
an alias record, not an identity reveal.

## 3. Rejected mentions

Strings that look like entities but must NOT become nodes: generic nouns, weather,
pure sensory abstractions, time expressions, and any span you judge to be a false
positive. Phase 2 uses these to measure precision honestly.

```json
{"surface": "", "paragraph": 0, "why": ""}
```

Note a known v1 behaviour when judging these: v1 emits lowercase common nouns as
entities (for example `quiet` is a `Concept` and `ledger` is an `Item` in this work).
Record what you believe is correct; do not try to match v1.

## 4. Relations

v1 has three tiers. **Annotate all three**, but know how v1 produces each, because
phase 2 will score them separately.

### Tier 1 — structural (`extraction_method = rule`)
v1 derives these with **no ML**: two entities whose mentions fall within a
`window_chars` character window in the same chapter become an edge, and the relation is
chosen from a fixed type-pair table (`storyweave/graph/builder.py`), with a lexical cue
promoting `MemberOf` to `LeaderOf`. `RelatedTo` is the never-drop fallback for any
co-occurring pair the table does not cover.

Type-pair table, verbatim from the code:

- Character -> Organization: `MemberOf`
- Character -> Place: `LocatedIn`
- Character -> Ability: `HasAbility`
- Character -> Item: `OwnsItem`
- Character -> Title: `HasTitle`
- Character -> Event: `ParticipatedIn`
- Organization -> Place: `LocatedIn`
- Organization -> Organization: `AffiliatedWith`
- Place -> Event: `ParticipatedIn`
- anything else: `RelatedTo`

Full Tier-1 vocabulary: `AffiliatedWith`, `LocatedIn`, `MemberOf`, `LeaderOf`, `HasAbility`, `OwnsItem`, `HasTitle`, `ParticipatedIn`, `RelatedTo`.

### Tier 2 — social (`extraction_method = curated` in this work)
`Ally`, `Enemy`, `Rival`, `Mentor`, `Student`, `Family`, `Parent`, `Child`, `Sibling`, `Spouse`, `Romantic`, `Betrayed`, `Serves`, `Killed`, `Protects`, `Fears`, `Respects`.

The LLM layer is OFF in this build (`llm_enabled = False`). The Tier-2 records present
in this work were **hand-curated from a story bible** and are tagged `curated`, never
`llm`. Annotate the social relations the text actually supports; v1's coverage here is
sparse by construction and phase 2 should show that.

### Tier 3 — identity (`extraction_method = curated` in this work)
`SAME_AS`, `ALIAS`, `SECRET_IDENTITY`, `REINCARNATION`, `TRANSMIGRATED_INTO`.

An identity relation is the showcase case: it is a claim that two entities the reader
believed distinct are one. Record the paragraph at which **the reader learns it**, which
is what v1 stores as `revealed_chapter` — not the paragraph where it first became true
in the story world (that is `first_seen_chapter`).

### What v1 actually emitted for this work

| relation | edges |
| --- | ---: |
| `RelatedTo` | 565 |
| `LocatedIn` | 347 |
| `OwnsItem` | 115 |
| `ParticipatedIn` | 113 |
| `LeaderOf` | 58 |
| `MemberOf` | 58 |
| `HasTitle` | 26 |
| `HasAbility` | 17 |
| `AffiliatedWith` | 8 |
| `Mentor` | 3 |
| `Serves` | 3 |
| `ALIAS` | 2 |
| `Parent` | 2 |
| `REINCARNATION` | 2 |
| `SECRET_IDENTITY` | 2 |
| `Protects` | 1 |
| `Respects` | 1 |
| `Rival` | 1 |
| `Sibling` | 1 |
| `TRANSMIGRATED_INTO` | 1 |

Schema relation types v1 produced **zero** of in this work — a real coverage gap, not a
schema gap:

- Tier 1 unused: none
- Tier 2 unused: `Ally`, `Enemy`, `Student`, `Family`, `Child`, `Spouse`, `Romantic`, `Betrayed`, `Killed`, `Fears`
- Tier 3 unused: `SAME_AS`

Relation object:

```json
{"source": "", "target": "", "relation": "", "tier": 1,
  "paragraph": 0, "evidence": "", "directed": true}
```

`relation` must be one of the 31
names listed above. `evidence` is a short verbatim quote.

## 5. Events

`Event` is a node type in v1, so a named event (a battle, a ceremony, a masque) should
appear in `entities` as well. The `events` array is for the occurrence itself: who took
part, where, and at which paragraph.

```json
{"name": "", "paragraph": 0, "participants": [], "place": "", "notes": ""}
```

## 6. Uncertain

Anything you could not decide. Phase 2 excludes these from the scored set rather than
guessing, so use it freely.

```json
{"item": "", "paragraph": 0, "question": ""}
```

## 7. Reveal stamps

Every v1 node, edge and property carries two chapter stamps:

- `first_seen_chapter` — the chapter in which the thing exists in the text.
- `revealed_chapter` — the chapter in which the READER learns it. The spoiler fence
  keys on this one.

For Tier-1 rule edges v1 sets them equal (a co-occurrence is known as soon as it
happens). For identity reveals they differ, and the difference is the point. If you can
tell that a fact is true earlier than the reader is told, say so in `notes`.

## 8. Provenance in the current database

Nodes by extraction method: `gliner`=206.
Edges by extraction method: `curated`=19, `rule`=1307.

`gliner` = zero-shot GLiNER (14 label prompts).
`rule` = the co-occurrence table above. `curated` = hand-written from the story bible.
`llm` = a real model run; **no record in this work carries it**, because the LLM layer
never ran.

## 9. What phase 2 will compute from this

Entity precision/recall/F1, alias F1, relation precision/recall/F1 per tier, and
ranking metrics (P@k, MAP, AUC) against the entities you mark as significant. None of
those can be computed before this annotation exists, which is why the v1 report lists
them as not measured.
