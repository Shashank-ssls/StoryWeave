# R3 — Four node types, titles become labels

**Goal:** remove the largest entity error category (type disagreement, 16/44) by
collapsing 8 types to 4, and give every entity a list of chapter-gated names.

## Paste into Claude Code
```
Read CLAUDE.md and docs/retrofit/R3_four_types_and_labels.md. Phase R3. R2 is complete.
```

## Preflight (every session in this phase)
`.\dev.ps1 -Ml` then `python tools/check_local_env.py` must pass before any
model load, download or pipeline run. If a model or package is missing, it is
downloaded only inside the repo (see CLAUDE.md table). Fail → stop and report.

## Tasks
1. `db/models.py`: `NodeType` = Character, Organization, Place, Item. Add
   `LEGACY_TYPE_MAP` documenting the v1 fate of each old type:
   Ability/Concept/Event → not a node (kept as mention rows, searchable);
   Title → label on the person it refers to (task 3), else not a node.
2. GLiNER labels in `nlp/labels.py`: prompt only the 4 types (keep prompt
   phrasing per work in `storyweave.toml`). Keep `species` as an optional
   Character attribute.
3. New table `entity_labels(entity_id, label, kind, revealed_chapter,
   is_primary, quote)`, kind ∈ full/short/title/epithet/description.
   Migration: add table; populate from existing canonical name + aliases.
   Display name at chapter n = most recent label with `revealed_chapter <= n`
   (SQL in repository, called through fence.py — this is a FENCE SURFACE).
4. Abbreviation merge rules in `nlp/cluster.py` (all must hold): contiguous
   word-subsequence of the full name; full form first or same chapter; within a
   configurable chapter window; not stop-word-only; short form does not match
   another entity's full name. When ambiguous: do NOT merge. Keep v1's
   0-over-merge behaviour.
5. Title linking: a title label attaches to a person only at the chapter the
   text connects them (quote required). Before that it is its own unlinked
   label/entity. No LLM needed; exact apposition patterns only
   ("X, the Warden", "the Warden, X").
6. Re-run extraction on The Ninth House 40 chapters into
   `data/retrofit/ninth_house_r3.db` (never the frozen DB).
7. Fence test: a title linked at chapter k is not linked in any payload at k−1.

## Scoring note (write it in the result file)
4-type entity F1 is scored against a 4-type projection of the annotation
(map annotation types with LEGACY_TYPE_MAP; drop non-node types). This is a
DIFFERENT answer key from v1 — never compute a delta against 0.532.

## Acceptance
- [ ] `tools/check_local_env.py --c-drive-report` passes and C: sizes match the R0 baseline (paste both)
- [ ] Migration test up/down on a fixture DB
- [ ] Label-reveal fence test passes
- [ ] Entity P/R/F1 per type with counts, alias P/R/F1 with over-merge and
      under-merge counts, in `evidence/retrofit/R3_RESULT.md` [MEASURED]
- [ ] Over-merges = 0 (if not, list each one and stop)
- [ ] Green gates, commit `feat(retrofit): R3 four types + entity_labels`, push
