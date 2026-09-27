# v1 error analysis — phase 2

> REFERENCE ANNOTATION: model-generated (GPT-5), one fresh session per chapter, single run each; paragraph indices, alias positions and evidence spans verified and corrected by hand; ch09 reindexed from 0- to 1-indexed. Every score below is AGREEMENT between two systems (StoryWeave v1 and GPT-5), NOT accuracy against human ground truth. See evidence/annotation/PROVENANCE.md.

Every false positive and false negative below was re-derived in this run by `tools/eval_errors.py` from the same inputs the scorer used. Categories were read off the actual cases and then written down as rules, which are printed next to their counts; a case is assigned to the FIRST rule it satisfies, so the categories partition the errors and each table's counts sum to its total.

Relation errors are analysed for the `chapter_local` variant (v1 edges with `first_seen_chapter == N`), which is the stricter of the two the scorer reports.

---

## Entities

### False positives — v1 produced, reference did not

23 entity false positives in total, across chapters 9, 17 and 37.

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `type_disagreement` | 8 | 2 | 5 | 1 |
| `reference_alias_kept_separate` | 3 | 2 | 0 | 1 |
| `reference_rejected_string` | 4 | 2 | 1 | 1 |
| `not_in_reference` | 8 | 4 | 4 | 0 |

**`type_disagreement` — 8**

Rule: v1's name matches a reference entity's name after normalisation, but the two assign it a different node type. Each of these is simultaneously a false positive and a false negative under the strict (name, type) match.

- ch9: 'Warden' (Character) — reference types it Concept
- ch9: 'House Vell' (Place) — reference types it Organization
- … and 6 more, all listed in `evidence/scores_v1.csv`.

**`reference_alias_kept_separate` — 3**

Rule: v1's name is listed by the reference as a surface_form or alias of some OTHER entity, i.e. the reference would have folded it into an existing entity and v1 kept it as its own.

- ch9: 'Drask' (Character) — reference folds it into 'Orin Drask'
- ch9: 'Captain' (Title) — reference folds it into 'Orin Drask'
- … and 1 more, all listed in `evidence/scores_v1.csv`.

**`reference_rejected_string` — 4**

Rule: v1's name is one of the strings the reference explicitly put in rejected_mentions for that chapter — the reference says it should not be an entity at all.

- ch9: 'quiet' (Concept) — reference reason: A sensory or behavioral abstraction rather than an entity.
- ch9: 'gilded rooms' (Place) — reference reason: A generic description of the interiors of Vell Hall, not a separate identifiable place.
- … and 2 more, all listed in `evidence/scores_v1.csv`.

**`not_in_reference` — 8**

Rule: v1's name appears nowhere in the reference for that chapter: not as an entity, not as a surface form or alias, not as a rejected mention. The reference simply does not mention the string.

- ch9: 'Corwin' (Character) — absent from the reference's entities, surface forms, aliases and rejected mentions
- ch9: 'Across the Quarter' (Place) — absent from the reference's entities, surface forms, aliases and rejected mentions
- … and 6 more, all listed in `evidence/scores_v1.csv`.

### False negatives — reference has, v1 does not

21 entity false negatives in total, across chapters 9, 17 and 37.

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `type_disagreement` | 8 | 2 | 5 | 1 |
| `canonical_name_choice` | 3 | 2 | 0 | 1 |
| `partial_span_only` | 6 | 4 | 1 | 1 |
| `absent_from_v1_chapter` | 4 | 3 | 1 | 0 |

**`type_disagreement` — 8**

Rule: the mirror of the FP rule of the same name: v1 has this name, with a different node type.

- ch9: 'Warden' (Concept) — v1 types it Character
- ch9: 'House Vell' (Organization) — v1 types it Place
- … and 6 more, all listed in `evidence/scores_v1.csv`.

**`canonical_name_choice` — 3**

Rule: v1 DID see this exact string as a mention in this chapter and clustered it, but named the resulting entity after a different surface form — so a strict name match fails even though the entity was found.

- ch9: 'Orin Drask' (Character) — v1 saw this exact surface and clustered it under 'Drask' (Character)
- ch9: 'Corwin Vell' (Character) — v1 saw this exact surface and clustered it under 'Corwin' (Character)
- … and 1 more, all listed in `evidence/scores_v1.csv`.

**`partial_span_only` — 6**

Rule: v1 has no mention equal to this name, but it does have a mention sharing a DISTINCTIVE word with it — the span boundary differs (typically a multi-word or possessive phrase v1 split). 'Distinctive' excludes the stoplist {the, a, an, of, and, s, house, lord, lady, ser, master, mistress, captain, warden}, which recur across unrelated names in this work and would otherwise make almost every pair look related.

- ch9: 'Salt Quarter watch' (Organization) — v1 has mentions sharing ['quarter', 'salt']
- ch9: "Undercroft's hidden door" (Item) — v1 has mentions sharing ['undercroft']
- … and 4 more, all listed in `evidence/scores_v1.csv`.

**`absent_from_v1_chapter` — 4**

Rule: v1 produced no mention in this chapter sharing any distinctive word with this name, using the same stoplist. A plain recall miss — though note that a name built ONLY from stoplisted words, such as 'Warden-Captain', lands here by construction rather than because v1 saw nothing nearby.

- ch9: 'Warden-Captain' (Title) — no v1 mention in this chapter shares a distinctive word
- ch9: 'Sorrel' (Character) — no v1 mention in this chapter shares a distinctive word
- … and 2 more, all listed in `evidence/scores_v1.csv`.

---

## Relations

### False positives — v1 edge with no reference counterpart

162 relation false positives in total, across chapters 9, 17 and 37.

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `cooccurrence_fallback_RelatedTo` | 81 | 60 | 15 | 6 |
| `cooccurrence_type_pair_rule` | 79 | 41 | 27 | 11 |
| `curated_tier2_or_tier3` | 2 | 1 | 0 | 1 |

**`cooccurrence_fallback_RelatedTo` — 81**

Rule: the edge is `RelatedTo`, the never-drop fallback `graph/builder.py` emits for any co-occurring pair its type-pair table does not cover.

- ch9: Drask -RelatedTo-> Casimir Lowe
- ch9: Drask -RelatedTo-> Ettie Marsh
- … and 79 more, all listed in `evidence/scores_v1.csv`.

**`cooccurrence_type_pair_rule` — 79**

Rule: the edge is a Tier-1 relation the type-pair table assigned from the two node types alone, on a co-occurrence the reference did not record as a relation.

- ch9: Drask -LocatedIn-> Salt Quarter — relation LocatedIn
- ch9: Drask -LocatedIn-> eastern docks — relation LocatedIn
- … and 77 more, all listed in `evidence/scores_v1.csv`.

**`curated_tier2_or_tier3` — 2**

Rule: the edge is a hand-curated Tier-2/Tier-3 record with no counterpart in the reference.

- ch9: Drask -Respects-> Juno Stray — relation Respects, tier 2
- ch37: Mira -TRANSMIGRATED_INTO-> Wanderer — relation TRANSMIGRATED_INTO, tier 3

### False negatives — reference relation v1 lacks

46 relation false negatives in total, across chapters 9, 17 and 37.

| cause | count | ch9 | ch17 | ch37 |
| --- | ---: | ---: | ---: | ---: |
| `endpoint_not_found_by_v1` | 38 | 16 | 12 | 10 |
| `tier2_social_not_produced` | 3 | 0 | 3 | 0 |
| `tier1_not_produced` | 5 | 1 | 2 | 2 |

**`endpoint_not_found_by_v1` — 38**

Rule: at least one endpoint of the reference relation is an entity v1 did not produce for this chapter, so the relation could not be matched at all.

- ch9: Orin Drask -LeaderOf-> Salt Quarter watch
- ch9: Orin Drask -HasTitle-> Warden-Captain
- … and 36 more, all listed in `evidence/scores_v1.csv`.

**`tier2_social_not_produced` — 3**

Rule: a Tier-2 social relation. The LLM layer is off in this build, and the curated Tier-2 records cover other pairs, so v1 has nothing to match.

- ch17: Lord Fennick Oswald -Sibling-> Brenna Oswald
- ch17: Brenna Oswald -Respects-> Corwin
- … and 1 more, all listed in `evidence/scores_v1.csv`.

**`tier1_not_produced` — 5**

Rule: both endpoints were found, but v1 holds no edge with this relation between them.

- ch9: Juno Stray -LocatedIn-> Bone Market
- ch17: Brenna Oswald -RelatedTo-> Corwin
- … and 3 more, all listed in `evidence/scores_v1.csv`.

---

## Rejected mentions v1 emitted

The reference lists 49 strings across the three chapters that it says should NOT become entities. v1 emitted **6** of them — either as an entity's canonical name or as a mention surface it clustered into an entity.

| chapter | rejected string | how v1 holds it | the reference's reason |
| ---: | --- | --- | --- |
| 9 | `quiet` | v1 canonical name of 'quiet' (Concept) | A sensory or behavioral abstraction rather than an entity. |
| 9 | `gilded rooms` | v1 canonical name of 'gilded rooms' (Place) | A generic description of the interiors of Vell Hall, not a separate identifiable place. |
| 17 | `ambition` | v1 canonical name of 'ambition' (Concept) | A personal quality rather than a named ability or independently established concept. |
| 17 | `rooms` | v1 mention surface of 'gilded rooms' (Place) | Generic physical spaces without individually identifiable locations. |
| 17 | `doors` | v1 mention surface of 'Undercroft' (Place) | Figurative references to opportunities rather than identifiable physical objects. |
| 37 | `Undercroft collapse` | v1 canonical name of 'Undercroft collapse' (Event) | The collapse is described as a past occurrence but is not given a distinct event name in the chapter. The location itself is annotated separately. |

**What kind of strings these are.** Read together, they are of three kinds, and the table above is the whole population, so this is a description of it rather than a sample:

1. **Abstract nouns used as atmosphere** — `quiet`, `ambition`. The reference rejects them as sensory or character qualities; v1 admits them as `Concept` entities in their own right.
2. **Generic architectural nouns** — `gilded rooms`, `rooms`, `doors`. The reference rejects them as unidentifiable spaces; v1 admits `gilded rooms` as a `Place` and folds `rooms` and `doors` into `Place` entities.
3. **An unnamed past occurrence** — `Undercroft collapse`. The reference rejects it because the chapter never gives the event a name; v1 admits it as an `Event`.

All of them are common nouns or common-noun phrases, none is a proper noun. That is consistent with the `Concept` prompt list in `storyweave/nlp/labels.py`, which deliberately asks GLiNER for common-noun ideas (`power system`, `phenomenon`, `language`) in addition to the eight type names.

