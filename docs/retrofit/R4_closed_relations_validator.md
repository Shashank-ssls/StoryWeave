# R4 — Twelve closed relations, the validator, one edge per pair

**Goal:** every edge is typed from a closed list, carries a quote that names
both people, and appears once with a weight. Fixes defects D1 and D2.

## Paste into Claude Code
```
Read CLAUDE.md and docs/retrofit/R4_closed_relations_validator.md. Phase R4. R3 is complete.
```

## Preflight (every session in this phase)
`.\dev.ps1 -Ml` then `python tools/check_local_env.py` must pass before any
model load, download or pipeline run. If a model or package is missing, it is
downloaded only inside the repo (see CLAUDE.md table). Fail → stop and report.

## Tasks
1. `db/models.py`: replace TIER1/2/3 lists with `RELATIONS` (the 12) and a
   `DOMAIN_RANGE` table:
   | Relation | Head | Tail | Symmetric | Closable |
   |---|---|---|---|---|
   | KIN_OF | C | C | no | no |
   | ROMANTIC_WITH | C | C | yes | yes |
   | ALLY_OF | C,O | C,O | yes | yes |
   | ENEMY_OF | C,O | C,O | yes | yes |
   | SERVES | C | C,O | no | yes |
   | MENTOR_OF | C | C | no | yes |
   | KILLED | C | C | no | no |
   | SAME_AS | C | C | yes | no |
   | MEMBER_OF | C | O | no | yes |
   | LEADS | C | O,P | no | yes |
   | OWNS | C,O | I | no | yes |
   | LOCATED_IN | C,O,P | P | no | yes |
2. Mapping from old producers (`nlp/relex.py` prompts, `nlp/identity.py`):
   Ally→ALLY_OF; Enemy→ENEMY_OF; Mentor→MENTOR_OF; Student→MENTOR_OF reversed;
   Parent/Child/Sibling/Spouse/Family→KIN_OF with `kin_role`; Romantic→
   ROMANTIC_WITH; Serves→SERVES; Killed→KILLED; SAME_AS/SECRET_IDENTITY/
   REINCARNATION/TRANSMIGRATED_INTO→SAME_AS (keep original as `subtype`);
   ALIAS→entity_labels, not an edge; Rival/Betrayed/Protects/Fears/Respects→
   dropped (logged). Relex prompts added for MEMBER_OF, LEADS, OWNS, LOCATED_IN.
3. New module `storyweave/extract/validator.py`. Every proposed edge passes, in
   order, else is rejected with a reason code written to
   `validator_rejections` table:
   a. quote is verbatim in clean text of chapter `quote_chapter`
   b. relation ∈ RELATIONS
   c. head/tail types match DOMAIN_RANGE
   d. both endpoints are stored entities
   e. KIN_OF guard: kin word attached by possessive genitive to a participant
      ("X's father", "his niece") OR same kin claim in ≥2 chapters. Vocatives
      and "like a sister" are rejected.
   f. grade: STATED iff the quote contains a label of head AND a label of tail
      AND a relation cue word (cue lists per relation in config). Else INFERRED.
   Only STATED edges are served (grade clause in the query, R6).
4. `revealed_chapter` = chapter of the earliest qualifying STATED quote.
5. Weight, not duplicates: unique key (work, relation, head, tail) — symmetric
   relations normalised to head_id < tail_id. Repeat evidence increments
   `weight` and keeps the earliest quote. Add columns `weight, grade, quote,
   quote_chapter, kin_role, surface_term, subtype`.
6. `graph/serialize.py`: stop projecting through `nx.DiGraph`. Build the
   Cytoscape payload directly from rows (or `MultiDiGraph` if networkx is still
   needed). Test: two different relations between the same pair both reach the
   payload; a SAME_AS edge is never relabelled.
7. Re-run relations on `ninth_house_r3.db` → `ninth_house_r4.db`.

## Acceptance
- [ ] `tools/check_local_env.py --c-drive-report` passes and C: sizes match the R0 baseline (paste both)
- [ ] Unit tests for each validator branch with real corpus strings, incl.
      "Am I not blessed to suddenly get such a wonderful little sister?" → rejected,
      "The Saint looked at his niece" → accepted (given entities)
- [ ] D1/D2 regression tests pass; payload edge count == fenced row count
- [ ] Rejection counts by reason, and relation P/R/F1 per type with counts,
      micro + macro, on the 12-relation projection of the annotation, in
      `evidence/retrofit/R4_RESULT.md` [MEASURED]. SAME_AS as counts, not F1.
- [ ] Green gates, commit `feat(retrofit): R4 closed relations + validator + weight`, push
