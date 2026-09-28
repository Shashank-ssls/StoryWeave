# R7 — Frontend: readable graph, timeline removed

**Goal:** a first-time, non-technical viewer can answer "who is X connected to,
and how?" within a minute. Keep the Heretic's Codex look; change behaviour.

## Paste into Claude Code
```
Read CLAUDE.md, docs/design/DESIGN_SPEC.md and docs/retrofit/R7_frontend_readability.md.
Phase R7. R6 is complete. Rule Zero applies to every step.
```

## Preflight (every session in this phase)
`.\dev.ps1` then `python tools/check_local_env.py` must pass. `npm install`
only inside `frontend/` (local `node_modules`, cache in `.local\npm_cache`).
Playwright browsers only in `.local\ms-playwright`. No `-g` installs.

## Tasks
1. **Remove the timeline.** Delete `frontend/src/codex/Chronicle/`, the
   `work-chronicle` route in `router/useHashRoute.ts` and `CodexApp.tsx`, every
   nav link, shortcut and landing-page mention. Old chronicle URLs redirect to
   the graph. Remove any API client code only it used.
2. **Remove every client-side filter** in `frontend/src/graph/` (viewModel,
   stemmaModel) and `StemmaCanvas.tsx` that hides nodes/edges by label, degree,
   or type. Search stays (it only highlights). Add a unit test asserting the
   rendered element count equals the payload count.
3. **Controls** (top bar, plain words): Chapter slider · "Show: Main cast (20) /
   More (50) / Everyone" · toggles "Groups", "Places", "Items" (off by default).
   Each change re-requests `/graph`; nothing filtered locally.
4. **Edges:** always-visible label from the directional label table
   (KIN_OF shows `surface_term` forward, neutral inverse backward; MENTOR_OF
   "teaches"/"trained by"; SERVES "serves"/"commands"; symmetric ones one word).
   Arrowheads only on directed relations. Edge width by `weight` (3 steps max).
5. **Nodes:** shapes locked — filled circle Character, outlined circle
   Organization, square Place, diamond Item. Label = display name from
   entity_labels at n. Size by salience rank (3 steps). Layout: cola/fcose with
   fixed seed; positions stable as the slider moves (reuse previous positions).
6. **Click a node** → side panel: display name, first seen chapter, ego list of
   "relation — person" rows each with the quoted sentence and its chapter;
   "Show only their connections" switches the canvas to the ego graph.
7. **Legend** always visible, one line per shape and "Lines only appear when the
   book states the relationship in a sentence. Click a line to read it."
8. **Empty/low states:** if the payload has < 3 edges, show a calm note
   ("Few stated relationships by chapter n") instead of a blank canvas.
9. Screenshots at 1280×720 and 390×844 for ch 10/20/40, default settings and
   "Everyone", via `tools/verify_shots.py` → `evidence/retrofit/shots/`.

## Acceptance
- [ ] `tools/check_local_env.py --c-drive-report` passes and C: sizes match the R0 baseline (paste both)
- [ ] No route, link or code reference to Chronicle/timeline remains (grep proof)
- [ ] Rendered element count == payload count (test)
- [ ] Every visible edge has a readable label at 1280×720 (inspect screenshots;
      describe what you see for each)
- [ ] `npm run build` + frontend tests + pytest/ruff/mypy green
- [ ] Commit `feat(retrofit): R7 readable graph, timeline removed`, push
