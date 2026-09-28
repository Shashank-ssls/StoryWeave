# R6 — Server-side importance, the four-clause query, API

**Goal:** the server decides who appears. The cast dial finally does something,
and nothing about the future leaks through the ranking.

## Paste into Claude Code
```
Read CLAUDE.md and docs/retrofit/R6_salience_and_query_layer.md. Phase R6. R5 is complete.
```

## Tasks
1. `storyweave/graph/salience.py`, run offline after extraction. Table
   `node_salience(node_id, chapter, score, rank)` for every chapter n, using
   ONLY data from chapters ≤ n (rule 7). Features, each min-max normalised within
   that chapter's candidate set, equal weights, summed:
   lifetime mentions ≤ n · recent mentions (last 10% of chapters ≤ n, min 3) ·
   chapter spread · has proper name · speaks dialogue (`" "` and `[ ]`, not `' '`)
   · STATED degree ≤ n. Rank ties broken by first_seen_chapter then id.
   Weights live in `storyweave.toml`; do NOT tune them on the answer key.
2. Significance gate for Characters: a node is eligible only if it has a proper
   name AND (≥3 chapters OR ≥5 mentions) by chapter n. Rank only eligible nodes.
3. `repository.graph_payload(work, n, cast_size, types, grade='STATED')` — ONE
   SQL query, clauses in this order with comments:
   ```sql
   WHERE e.revealed_chapter <= :n   -- SAFETY: spoiler fence
     AND hs.revealed_chapter <= :n AND ts.revealed_chapter <= :n  -- SAFETY
     AND ns.chapter = :n AND ns.rank <= :cast_size   -- display: cast dial
     AND node.type IN (:types)                       -- display: overlays
     AND e.grade = :grade                            -- display: evidence
   ```
   Ring-2 relations are returned only when their overlay type is requested.
   Called only through `query/fence.py`.
4. Ego endpoint: `GET /works/{slug}/entity/{id}/ego?chapter=n` — the node plus
   1-hop STATED neighbours (cap 12 by rank) with quotes. 404 if the node is
   unrevealed at n.
5. `/graph` params: `chapter`, `cast` ∈ {20, 50, all} default 20, `types`
   default `Character`. Fix D3: `/works/{slug}/status` count goes through fence.
6. Extend the fence harness to the new surfaces: entities, edges, labels, ego,
   status count, salience (a node absent at n must not appear in any rank list
   at n). Keep the negative controls: injected canary per surface, and an
   unfenced repository that must produce violations.
7. Compute salience AUC / P@10 / P@20 / MAP vs the annotation `significant` flag.

## Acceptance
- [ ] Cast 20 / 50 / all produce different payloads at ch40 (the v1 no-op is gone)
- [ ] Fence: 0 violations over every chapter × surface × cast × types
      combination, with the tested surface list; every negative control fires
- [ ] Salience metrics and ch 10/20/30/40 density table in
      `evidence/retrofit/R6_RESULT.md` [MEASURED]
- [ ] Green gates, commit `feat(retrofit): R6 salience + four-clause query + ego API`, push
