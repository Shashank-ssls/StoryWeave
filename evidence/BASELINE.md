# Baseline freeze

Frozen: 2026-09-27
Source: `storyweave-demo.sqlite` (847,872 bytes, repo root)
Frozen copy: `evidence/v1_ninth_house.db` (read-only)
Commit: `00dbcfec0ab9c1466fbbcfe0dd2e9d93f553c5fd`
Branch: `integration/demo-scale`

Copy verified byte-identical to the source at freeze time
(SHA-256 `C7264C16DBD9223BBDB0EECEB4699E0243BA8A93130B544D351FDFE5FDD946FF`,
both files), `PRAGMA integrity_check` = `ok`, `IsReadOnly` = `True`.

## Contents

Two works: `the-hollow-crown` (id 1) and `the-ninth-house` (id 2).
**219 nodes, 1340 edges across BOTH works combined.**
All Ninth House figures must be scoped to `work_id = 2` / `work = the-ninth-house`,
which alone holds **206 nodes and 1326 edges** across 40 chapters.
`data/storyweave.sqlite` (122,880 bytes) contains 0 works and is not part of the baseline.

## Verified in code at this commit

The API applies the **spoiler fence only**. There is no server-side salience rank, no
server-side cast cap, and no disparity filter anywhere in the codebase — a search for
`salience|disparity` across `.py`/`.ts`/`.tsx`/`.toml` returns zero code hits at this
commit (matches appear only in prose in `PROGRESS.md`, `README.md`, `SETUP_NOTES.md` and
`docs/design/FRONTEND_OVERHAUL.md`).

Server path:
`storyweave/api/app.py:266` `get_graph()` -> `:268` `graph_json()` ->
`storyweave/graph/serialize.py:19` `build_graph()`, filtering via
`fence.visible_nodes` / `visible_edges` / `visible_node_properties`.

### Correction to an earlier description of the client-side filter

An earlier draft of this note described the client-side reduction as "salience demotion
using a lowercase-label heuristic, composed with a client-side min-degree filter". **That
is not what this commit contains.** That describes the pre-redesign Phase 8 frontend,
which the R0–R9 "Heretic's Codex" redesign superseded; `isBackground`, the
`label === label.toLowerCase()` heuristic and the min-degree slider no longer exist in
`frontend/src`.

What this commit actually contains, in `frontend/src/graph/`:

1. `viewModel.ts:57` `kindOf()` — Concept/Event nodes are diverted to "Also mentioned"
   and Title/unknown types are dropped, so they are never drawn.
2. `viewModel.ts` `buildViewModel()` — drops any identity edge with no `evidence_span`
   (the R8 citation gate), then merges parallel edges on the **unordered** node pair, an
   identity edge absorbing a social/structural one. Degree is computed over merged edges.
3. `stemmaModel.ts:49` `visibleGraph()` — the cast rule, in full:
   `cast === "everyone" || n.degree >= 2 || ids.has(n.id) || n.id === opts.focusId`.
   Edges are then kept only where both endpoints survived.

The only cast control in the UI is the Stemma's two-state toggle (`principal` /
`everyone`). It takes a mode, not a size; there is no cast-size number to record.

## Measured defects in the baseline architecture

**1. Parallel-edge collapse.**
`build_graph` projects into `nx.DiGraph`, which cannot hold parallel edges, so a second
edge on the same **ordered** pair overwrites the first and same-direction duplicates never
reach the client: **1326 fenced rows at ch.40 collapse to the 1316 served** (verified
against the live endpoint). Reciprocal pairs `(s,t)` and `(t,s)` both survive, because the
graph is directed. The loss happens in the projection layer *after* `query/fence.py` has
returned its rows, so the payload is not exactly the fenced set — the discrepancy is
outside the fence's control and invisible to it.

**2. Identity edge relabelling.**
The collapse in (1) can overwrite the relation type of an identity edge. At ch.40, edge
1325 `SECRET_IDENTITY (14 -> 150)` is overwritten by edge 1327 `REINCARNATION` on the same
ordered pair. This is why `SECRET_IDENTITY` counts read **1, 2, 2, 1** across chapters
10/20/30/40 instead of increasing monotonically. Given that rule #1 of the project is that
the graph models revealed reader-knowledge, a reveal changing type in the projection layer
is the more serious of the two defects.

**3. Principal cast filter is a no-op on this work.**
`rendered_view` and `rendered_everyone` are identical at every chapter
(74/369, 108/569, 127/709, 157/989). No drawable node in The Ninth House has degree < 2
(`deg0 = 0`, `deg1 = 0` at both ch.10 and ch.40), so the `degree >= 2` clause excludes
nothing. The 206 -> 157 node reduction is entirely `buildViewModel`'s node-type drops, not
cast reduction. Confirmed in the CSVs and independently in the live DOM.

Neither (1) nor (2) was fixed. Both are recorded as properties of the baseline
architecture and are addressed by design in the rebuild: edge weight replaces duplicate
rows, so there are no parallel edges for a DiGraph to collapse.

## Purpose

This is the "before" for the rebuild comparison. It cannot be regenerated once the
extraction pipeline changes. **Do not modify.**

## Backup note

`*.db` is gitignored (`.gitignore:11`), so `v1_ninth_house.db` is **not** tracked in git
and is **not** on GitHub. An external copy of `evidence/` is currently its only backup.
The rest of `evidence/` (CSVs, plates, plots, `REPORT.md`) and the harness in `tools/` are
committed and pushed, and the CSVs/plates/plots can be regenerated by re-running
`tools/run_evidence.py` — this database and this file cannot.
