# R6 — salience, the four-clause query, the ego API, and defect D3

| field | value |
| --- | --- |
| date | 2026-09-29 |
| branch | `retrofit/v2-core`, phase R6 |
| output DB | `data/retrofit/ninth_house_r6.db`, from `ninth_house_r5.db` (the clean R5 run) |
| models | none. This phase is arithmetic over stored mentions; no model was loaded |
| pre-registration | `docs/retrofit/RETROFIT_PROGRESS.md`, commit `4114cd8`, never edited |

Logs: `logs/R6_build_db.log`, `logs/R6_report.log`, `logs/R6_salience_score.log`,
`logs/R6_eval_fence.log`. Every figure **[MEASURED]**.

---

## 0. Headline

**The cast dial works, the status count no longer leaks, and the ranking is roughly twice
as good as v1's — but two of the five pre-registered numbers were missed, one high and
one low.**

| quantity | pre-registered | measured | |
| --- | --- | ---: | --- |
| salience **AUC** | 0.70 – 0.92 | **0.6667** (ch9 only; undefined elsewhere) | missed low |
| salience **P@10** | 0.55 – 0.85 | **0.8750** | missed high |
| default-view dots ch10 | 8 – 20 | **10** | inside |
| default-view dots ch20 | 15 – 20 | **7** | **missed** |
| default-view dots ch40 | 20 | **12** | **missed** |

The dots misses have one mechanical cause, explained in §3, and it is a design question
rather than a bug — I have **not** changed the behaviour to hit the band.

---

## 1. Salience — [MEASURED]

Features, equal weight, fixed in the pre-registration: `lifetime_mentions`,
`recent_mentions`, `chapter_spread`, `has_proper_name`, `speaks_dialogue`. Each min-max
normalised within that chapter's candidate set. **Edge degree is not a feature**, a
deliberate departure from the R6 phase doc — R1 measured v1's degree ranking collapsing
from P@10 0.4000 to 0.3000 the moment the co-occurrence edges were removed, and ranking a
cast by extraction recall that R4–R5 measured near zero would repeat that mistake.

4,020 rows over 40 chapters. Eligible cast after the significance gate (proper name AND
(≥3 chapters OR ≥5 mentions)): ch1 13, ch5 39, ch10 64, ch20 107, ch30 131, ch40 166.

| metric | R6 | v1 (R0, degree) | v1 (after R1) |
| --- | ---: | ---: | ---: |
| P@10 | **0.8750** | 0.4000 | 0.3000 |
| P@20 | **0.8750** | — | — |
| MAP | **0.9033** | 0.4414 | 0.3668 |
| AUC | **0.6667** (ch9 only) | — | — |

Per chapter: ch9 AUC 0.6667 / P@10 0.6250 / MAP 0.7100 · ch17 P@10 1.0000 · ch37 P@10 1.0000.

### The caveat that matters more than the headline

**At chapters 17 and 37 every matched reference entity is flagged `significant`.** There
are no negatives, so AUC is undefined there and P@k cannot score below 1.0 however the
nodes are ordered. The pooled P@10 of 0.8750 is therefore carried by two chapters where
the metric cannot discriminate, and the only informative chapter is ch9, at 0.6250.

The matched sets are also small — 8, 10 and 7 nodes — because only entities the reference
knows about can be scored. **This is a thin evaluation surface and the AUC band was
missed on the one chapter that could measure it.** The honest summary is that the ranking
is clearly better than v1's on the same key, and that the key is too small to say by how
much.

---

## 2. The four-clause query

```sql
WHERE n.work_id = ?
  AND n.revealed_chapter <= ?        -- FENCE (safety)
  AND s.chapter = ? AND s.rank <= ?  -- DISPLAY: the cast dial
  AND n.type IN (...)                -- DISPLAY: the requested overlays
```
```sql
WHERE e.work_id = ?
  AND e.revealed_chapter <= ?                    -- FENCE (safety)
  AND hs.revealed_chapter <= ? AND ts.revealed_chapter <= ?   -- FENCE (both endpoints)
  AND e.source_id IN (...) AND e.target_id IN (...)           -- DISPLAY: drawn endpoints
  AND (e.grade IN ('STATED','INFERRED') OR e.grade IS NULL)   -- DISPLAY: evidence
  AND (e.relation <> 'SAME_AS' OR e.grade = 'STATED')         -- DISPLAY: identity is strict
```

The fence clauses come first and are never merged with the display clauses (rule 1).
`grade IS NULL` keeps a pre-R4 database serving — the frozen baseline's rows have no
grade at all, and dropping them would blank it.

### The cast dial finally binds — defect D3, [MEASURED]

(nodes, edges) through the real API:

| chapter | cast=20 | cast=50 | cast=all |
| ---: | --- | --- | --- |
| 10 | (10, 4) | (10, 4) | (32, 10) |
| 20 | (7, 5) | (14, 8) | (41, 14) |
| 30 | (11, 10) | (21, 16) | (43, 21) |
| 40 | **(12, 7)** | **(24, 21)** | **(53, 27)** |

**At ch40 the three settings give three different payloads.** In v1 the filter was
client-side and changed nothing.

### Overlays at ch40 — each opt-in, default is Characters only (rule 2)

| types requested | dots | lines |
| --- | ---: | ---: |
| Character | 12 | 7 |
| Character, Organization | 14 | 18 |
| Character, Place | 18 | 10 |
| all four | 20 | 21 |

### Grade mix in the default view at ch40

STATED 1 · INFERRED 6 · **INFERRED share 85.7%** · SAME_AS served 0 (the STATED-only
guard holds) · **every served edge carries a quote: true**.

---

## 3. Why the dots predictions missed — mechanism, not a bug

The pre-registered clause order is **cast rank → node type**, which the user fixed and
which this implements literally. The rank is computed over *all* entity types, so
"cast 20" means *the top twenty entities*, and the type clause then removes the
non-Characters from that twenty. At chapter 40 only **12 of the top 20 are Characters**,
so a reader asking for "the main 20" sees 12 dots.

I predicted 20 because I had assumed the rank would be computed within the requested type
set. It is not, and **I have not changed it to match my prediction** — the clause order
was specified, and silently re-ordering it after seeing a number I did not like is exactly
the move this project's pre-registration discipline exists to prevent.

It is still a genuine usability defect, of the same family as D3: the number on the dial
does not correspond to anything the reader can count on screen. **Recommendation for R7:
rank within the requested type set** (one window function over the filtered set), so
"main cast 20" means twenty Characters. That is a one-clause change and a decision for
you, not for me to take unilaterally mid-phase.

---

## 4. The ego endpoint

`GET /works/{slug}/entity/{id}/ego?n=` returns the entity and its 1-hop neighbours, each
with **relation, grade and quote** — the three things v1's side panel lacked when it said
only "linked". Neighbours are ordered by salience rank and capped (default 12).

Measured at ch40 for Sorrel:

```
LOCATED_IN   The Undercroft  [STATED]   'They salvaged what they could from the Undercroft by lamplight'
MENTOR_OF    Thessaly        [INFERRED] 'when Sorrel came asking, and Sorrel would later be grateful'
MENTOR_OF    Vesper          [INFERRED] "returned with a name Sorrel had not heard before: Kaelen's G"
MEMBER_OF    The Choir       [INFERRED] "Sorrel's first instinct was to run. Her second, stronger one"
MEMBER_OF    the Council     [INFERRED] 'The Regency Council met for the first time three days after'
```

A non-existent or unrevealed id returns **404**, measured. An unrevealed entity must not
be distinguishable from one that does not exist, or the 404/200 split leaks by itself.

---

## 5. Defect D3 — the status count now goes through the fence

`node_count` by chapter: **n=1 → 17, n=10 → 86, n=40 → 191.** v1 returned the book-wide
total at every chapter, which told a chapter-1 reader how large the cast eventually gets —
a number leak even though no name escapes.

`test_the_status_count_goes_through_the_fence` **fails against the old behaviour** by
construction: it asserts that the fenced count at chapter 1 *differs* from
`repo.count_nodes`, so reverting the endpoint turns it red rather than letting it pass.

---

## 6. Fence — [MEASURED]

**0 violations over 28,046 elements across 12,660 queries**, every chapter × surface.
Both negative controls fire (12 and 198 violations detected); `DETECTOR VERIFIED TO FIRE:
True`.

Surfaces now swept, with the three added this phase in bold:

| surface | element kinds |
| --- | --- |
| `/entities` | entity |
| `/graph` | graph_node, graph_edge, graph_node_property, graph_node_label |
| `/entity/{id}` | detail_entity, detail_edge, detail_property |
| **`/entity/{id}/ego`** | **ego_entity, ego_neighbour** |
| **`/status`** | **status_count** |
| **salience ranking** | **salience_rank** |
| `/arcs` | arc_name |

Salience is not an HTTP surface, but the cast dial reads it, so it is swept directly: a
node unrevealed at *n* must not appear in any rank list at *n*, or the ordering itself
leaks who matters later. The status check is arithmetic rather than per-element — the
count must never exceed the number of nodes the fence allows.

---

## 7. Two bugs this phase found in existing code

1. **The API was silently dropping `grade` and `quote` from every edge.** The serializer
   emitted them; `GraphEdgeData` has no extra fields, so the response model removed them
   again. Rule 4 as amended *requires* every served edge to carry its verbatim quote, and
   the UI cannot draw STATED and INFERRED differently without the grade. Found by
   measuring the grade mix and getting 0 STATED / 0 INFERRED across 7 edges.
2. **`/status` had no chapter parameter at all**, which is why D3 was invisible: there was
   no *n* to fence against. It now takes one, defaulting to 1.

### A deliberate contract change, stated not buried

R6 changes the `/graph` endpoint's **defaults** to Characters-only at cast 20 (retrofit
rule 2's default graph). Six existing tests asserted the old default composition. They now
pass `cast=all&types=Character,Organization,Place,Item` explicitly, with a comment saying
why: they are about the fence and the seeded ontology, not about the default view, and
**what they assert is unchanged**. `graph_json`'s own defaults were left serving the whole
drawable graph, so the display policy lives in one place — the API — rather than two.

---

## 8. Gates

ruff `All checks passed!` · mypy `no issues found in 79 source files` ·
pytest **305 passed, 6 skipped** (287 → 305, 18 new) · C: byte-identical to the ledger
(`.ollama` 2,284 B, `%LOCALAPPDATA%\Ollama` 276,845 B, `.cache` 135.76 MB, no new items).

---

## 9. Viva defense

R6 is the phase where the display layer finally became real: the cast dial produces three
different payloads at chapter 40 where v1's produced one, the status count stops reporting
a book-wide total to a chapter-1 reader, and the ego endpoint answers "how are these two
related, and where does the book say so?" with a relation, a grade and a quote. The
ranking is defensible because of what it leaves out — edge degree, which R1 had already
measured collapsing — and the metrics are reported with the caveat that guts them: two of
the three annotated chapters contain no negatives at all, so the headline P@10 of 0.875 is
carried by chapters where no ordering could have scored worse. Two pre-registered numbers
were missed and neither was rescued: the AUC band on the one chapter that could measure
it, and the dots count, whose cause I traced to the specified clause order and left in
place rather than re-order after the fact.
