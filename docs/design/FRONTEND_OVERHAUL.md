# StoryWeave — Frontend Overhaul Execution Playbook

> **Audience:** the Claude Code session that builds the redesign.
> **Authority order:** `docs/design/DESIGN_SPEC.md` (what to build) > this file (how to build it) > the PDF canvas (visual reference) > old `DESIGN.md` (superseded, historical only).
> **Read this whole file before touching code. Re-read §2 and §5 at the start of every phase.**

---

## 0. Mission

Replace the Phase 8 "constellation" frontend with **"The Heretic's Codex"**, exactly as specified in `docs/design/DESIGN_SPEC.md`, in React + Cytoscape.js. Backend is frozen. The result must look like the canvas artboards in `docs/design/StoryWeave_Redesign_Directions.pdf`, verified by real browser screenshots, not by "it compiles".

Stack decision (final, do not revisit): **React + Vite + Cytoscape.js + cytoscape-cola, verified with Playwright.** Flutter is explicitly rejected: the spec is built on CSS tokens, `@fontsource` web fonts, Cytoscape stylesheets and DOM-level fence testing; a Flutter rewrite would discard the working graph layer and the network-log fence verification for no gain.

---

## 1. Files and where they live

At the start of Phase 0, place the design package in the repo (they will already be in the repo root or `docs/design/` — find them, then normalise):

| File | Final location | Role |
|---|---|---|
| `DESIGN_SPEC.md` | `docs/design/DESIGN_SPEC.md` | The spec. Section numbers (§) below refer to it. |
| `StoryWeave_Redesign_Directions.pdf` | `docs/design/` | 7 artboards: Landing, Dossier, Stemma, Chronicle, Reveal, Change chapter, States. |
| `tokens.css` | `docs/design/` (reference) **and** copied into `frontend/src/styles/tokens.css` (live) | Single source of truth for colors/type/space/motion. |
| `cytoscape-style.js` | `docs/design/` (reference) **and** ported to `frontend/src/graph/codexStyle.(ts|js)` | Graph stylesheet. |
| `mural-codex.svg` | `frontend/src/assets/mural-codex.svg` | Placeholder backdrop art. |
| `FRONTEND_OVERHAUL.md` (this file) | `docs/design/FRONTEND_OVERHAUL.md` | Execution rules + progress log (§9). |
| old `DESIGN.md` | leave in place; add one line at the top: `> SUPERSEDED by docs/design/DESIGN_SPEC.md (Heretic's Codex).` | History. |

Use the frontend's existing language (TS or JS). If the frontend is TypeScript, port the style file to TS with proper types. Do not convert languages.

---

## 2. Hard rules (apply to every phase)

1. **Backend is frozen.** No changes to Python, SQL, API routes or payload shapes. If the spec needs data the API doesn't return, implement the spec's stated fallback (§13 of the spec) and log it in §9 under "Backend deps hit". Never fake data in the UI to cover a gap.
2. **Local only.** All npm packages are project-local (`devDependencies`/`dependencies`), never `-g`. Playwright browsers install inside the project: set `PLAYWRIGHT_BROWSERS_PATH` to `<repo>/.local/ms-playwright` via `dev.ps1`/`dev.bat` (session-scoped, not setx) and in the npm scripts using `cross-env`. Nothing lands in `C:\Users\...`. Verify once after install.
3. **Fence rules F1–F9 (spec §9.1) are invariants, not features.** They get automated tests (Playwright network assertions + unit tests) the moment the chapter model exists (Phase 3), and those tests run in every later phase. A phase that breaks a fence test is not green, regardless of how good it looks.
4. **Red discipline (spec P2).** `--accent` / `--accent-hi` / `--accent-soft` may appear only in: identity edges, reveal UI, bookmark marker, "changed" tags, the landing kicker, the fence-relevant chapter "next" stepper button, and checkbox accent-color in the Stemma filter (canvas shows it). Any other usage is a bug. Enforce with a grep check (§4.3).
5. **Pirata One ≥ 28px only. No uppercase + letter-spacing anywhere. Radius 0 everywhere except circles. No emoji. No drop shadows** except dialog/reveal scrims.
6. **Tokens only.** No raw hex colors, font-family strings, or magic durations in components. Everything references a CSS custom property from `tokens.css`. The only exception is the Cytoscape style module, which mirrors tokens as literals (Cytoscape can't read CSS vars); keep it in one file with a comment pointing to tokens.css.
7. **No developer UI in the reader UI (spec P8).** Delete old counters, MIN LINKS, stats bars, debug readouts. Don't hide them with CSS; remove them.
8. **Don't gold-plate.** Build only what the current phase lists. No extra themes, no light mode, no settings pages, no animations the spec doesn't describe.
9. **Delete, don't accumulate.** When a new component replaces an old one, remove the old component, its CSS and imports in the same phase. Run the existing lint/type checks; they must stay clean (the project was mypy/ruff clean; keep ESLint/tsc at zero new errors).
10. **Phase discipline.** One phase = one green boundary = one commit + push. Never start phase N+1 in the same working state as an unfinished phase N. Never bundle phases into one commit.
11. **Honesty labels.** Every claim in your phase report is **MEASURED** (you ran it and saw it: screenshot, test output, network log), **ASSERTED** (reasoned but not verified) or **BROKEN**. Never write "works" without MEASURED evidence.
12. **Stop conditions.** Stop and ask me (don't improvise) if: the spec contradicts itself in a way that changes layout or behaviour; a backend dependency blocks a MUST requirement with no spec fallback; a phase would require touching backend code; the same failure persists after two genuinely different fix attempts.
13. All work happens on branch `redesign/codex`. main is the frozen, showable old version until Phase 9 is green and I merge.
---

## 3. Phase 0 — Recon + verification harness (no visual changes)

Goal: understand the current frontend and build the tool that proves every later phase.

1. **Recon (read-only).** Map `frontend/`: entry point, component tree, state management, how it fetches `/works` and `/graph?n=`, the exact payload shape (capture a real response for the Hollow Crown demo at every chapter 1..4 and save to `frontend/tests/fixtures/hollow-crown/graph-n{1..4}.json`), `ontology.ts` relation enums, current routing (spec says none), where Cytoscape is initialised. Write findings to §9 "Recon".
2. **Verify backend deps D1, D4 against the captured payloads** (quote clause on identity edges? alias lists?). Record exact field names or "ABSENT → fallback" in §9. This decides later phases, so be precise.
3. **Install Playwright locally** (`@playwright/test` as devDependency, Chromium only, into `.local/ms-playwright`). Add `.local/` to `.gitignore` if not present.
4. **Build `frontend/scripts/shoot` (Playwright)** — the visual harness:
   - Boots against the running dev server (document the two-terminal start in §9, or use Playwright's `webServer` config to start Vite; backend must already be running via `dev.ps1`).
   - Takes named screenshots at **1440×900 and 1280×720** of a list of routes/states given as config, saves to `frontend/.shots/<phase>/<name>@<w>.png` (gitignored).
   - Records every network request; writes `network.json` per shot.
   - Records browser console errors and fails the run on any.
   - One command: `npm run shoot -- --phase=<id>`.
5. **Build the fence test suite skeleton** (`frontend/tests/fence.spec.*`) with the network-log helper `assertNoGraphRequestAbove(n)`. Tests that need later features are written as `test.fixme` with the spec rule id in the name (F1…F9), so the gap is visible.
6. **Baseline shots** of the current (old) UI → `.shots/phase-0/`. These are the "before" pictures.
7. Green = harness runs end-to-end on the old UI with zero console errors; fixtures captured; D1/D4 verdicts recorded. Commit: `chore(frontend): phase 0 recon + playwright harness`.

---

## 4. Visual verification protocol (every phase from 1 on)

### 4.1 The loop
For each screen/state touched in the phase:
1. `npm run shoot -- --phase=<id>` at 1440×900 and 1280×720.
2. **Open the screenshots and look at them** (use the image viewer; don't skip this). Open the matching PDF artboard page next to it.
3. Write a comparison table in the phase report: row per element of the relevant spec section → `matches / deviates (how) / missing`. Measure from the screenshot where possible (column widths, font sizes via computed style in Playwright, colours via `getComputedStyle`).
4. Fix deviations, re-shoot. Max **3 fix loops** per screen; after that, log remaining deviations as ASSERTED-acceptable or BROKEN and move on.

### 4.2 Computed-style assertions (automated, cheap, catch drift)
Add Playwright checks, per phase, for the rules a screenshot can't reliably prove:
- every element with `font-family` containing Pirata One has `font-size ≥ 28px`;
- no element has `text-transform: uppercase` with `letter-spacing > 0`;
- all `border-radius` values are `0px` except elements tagged `data-round`;
- the fonts actually loaded (`document.fonts.check('16px "EB Garamond"')` etc.), not fallbacks;
- no horizontal page scroll at 1280×720 (`scrollWidth <= clientWidth`).

### 4.3 Static checks (grep, part of `npm run lint:design`)
- raw hex (`#[0-9a-fA-F]{3,8}`) outside `tokens.css` and the Cytoscape style file → fail;
- `var(--accent` in any file not in the allow-list of red-permitted components → fail (list the allowed component files explicitly in the script);
- `font-family:` literal outside tokens → fail.

### 4.4 What "green" means for a UI phase
All of: shots taken and inspected; comparison table written; fence tests pass; computed-style + static checks pass; lint/type check clean; zero console errors; old code replaced by this phase deleted. Then commit + push.

---

## 5. Phase plan

Follow spec §15 order. Each phase lists: scope → spec sections → done-when. Anything not listed is out of scope for that phase.

**Phase 1 — Tokens & typography.**
Install `@fontsource/pirata-one`, `@fontsource/eb-garamond`, `@fontsource/alegreya-sans`. Wire `tokens.css` globally. Replace old global styles/fonts/palette. Build a hidden dev route `#/_type` rendering the type scale, colour swatches, buttons (all variants/states from spec §10 `Button`), tabs, inputs, the ornament rule, and all 9 icons (§4.4) as inline SVG components.
Done-when: `_type` screenshot shows every token; computed-style checks pass; old fonts (Spectral, IBM Plex) and old palette removed from the codebase.

**Phase 2 — Shell.**
Router (hash routing is fine; routes per spec §5; bookmark NOT in URL). Mural + vignette fixed layers, three-column layouts for Dossier/Stemma, Chronicle header layout, tabs switching routes, theme-strings object (spec §12) — all copy comes from it. Screens may contain placeholder content boxes but real layout dimensions.
Done-when: shell screenshots of all three tabs at both widths match the artboard geometry (rail widths, paddings); no horizontal scroll at 1280.

**Phase 3 — Chapter model + fence.** *(most important correctness phase)*
Bookmark state per work in `localStorage` (`storyweave:bookmark:<slug>`); `ChapterListCompact`; `ChapterDialog` (spec §6.6, all behaviours incl. digits-only, clamp, no fetch while typing, arc fallback blocks of 100); fetch layer with single in-flight request + AbortController; payload cache with purge on backward move; forward/backward flows (spec §8.1) minus the reveal overlay (stub it with a console-free placeholder toast); `[` `]` keys; error rule (keep previous data + banner, don't advance bookmark); Roman numeral helper (`roman(n)` if n ≤ 39).
Tests (un-fixme them): F1 no request above bookmark on every flow incl. rapid double confirm; F5 purge; F2/F3 sealed row constant; aborted responses never render; error banner path (use Playwright route interception to fail a request).
Done-when: all fence tests pass MEASURED with network logs attached to the report.

**Phase 4 — Dossier.** Spec §6.2 complete: rail cast list (degree sort, groups, "changed" tags via n vs n−1 diff, overflow), H1/lede/ornament, identity blocks (quote per D1 verdict), ties grid, fence line with tooltip, ego graph (concentric), entity-not-present state. Default landing inside a work = dossier of highest-degree person.

**Phase 5 — Stemma.** Spec §6.3 + §7 complete: port codexStyle, view-model builder (kind mapping §7.1, Title never a node, Concept/Event excluded, parallel-edge merge with identity absorbing social, quote-missing identity edge dropped with console.warn — note: console.warn is allowed, console.error is not), cola physics settings §7.6, focus mode §8.3, principal filter + org folding badge, zoom tiers §7.5, selection panel, search (fenced aliases only), canvas centre mask.
Extra verification: generate a **synthetic 100-node fixture** (client-side test fixture only, clearly named `synthetic-100.json`, never shipped as demo data) and screenshot the default fit — principal labels must not overlap.

**Phase 6 — Reveal.** Spec §6.5 + §8.2: diff-driven trigger, choreography timings, pager for ≤3, summary sheet for big jumps, quiet mode preference, replay buttons in Dossier, 3s highlight on close, aria-live. Verification: Playwright screenshots at t = 0, 450, 1000, 1400ms (use `page.clock` or slowed animations) + reduced-motion run.

**Phase 7 — Chronicle.** Spec §6.4: small-N columns first, proportional/large-N path with block fallback, presence threads, stitches, identity links, bookmark line, constant-width sealed band, right panel with reveal cycling and "Read on" → confirm flow.

**Phase 8 — Landing & states.** Spec §6.1 + §6.7: landing with live try-it stepper (mini-graph obeys F9: test it), "How the seal works" explainer, all state cards, empty shelf, demo-missing, error behaviour.

**Phase 9 — Polish.** Spec §11 + §8.5: reduced motion everywhere, full keyboard map + `?` sheet, screen-reader mirror of focus neighbourhood, 1024–1279 drawer behaviour, favicon, run spec §16 acceptance checklist and report each line MEASURED/ASSERTED/BROKEN.

---

## 6. Engineering conventions

- Components per spec §10 inventory, one folder each where they have styles. CSS Modules or plain CSS files with token vars — follow whatever the current frontend uses; don't introduce Tailwind or a CSS-in-JS library.
- Graph view-model builder (`graph/viewModel`) is a **pure function** `(payload, options) → {nodes, edges}` with unit tests (Vitest if present, else add it locally): kind mapping, merge rules, Title exclusion, missing-quote drop, principal filter. The fence is a data-layer invariant in this project; the view model is where the UI's share of it lives, so it is tested like data code, not UI code.
- Diff function (`graph/diff`) pure + unit tested: new nodes, new edges, new identity edges between two fenced payloads.
- No new runtime dependencies beyond: fontsource packages, a tiny router only if hand-rolled hash routing gets messy (prefer hand-rolled). Dev deps: Playwright, cross-env, Vitest if missing. Ask before adding anything else.
- Accessibility baseline in every component: real buttons/links/inputs, visible focus ring (`--focus-ring`, never red), 44px targets.

---

## 7. Phase report template (post in chat AND append to §9)

```
## Phase <n> — <name> — GREEN | NOT GREEN
Scope delivered: …
Spec sections covered: §…
Visual comparison (artboard <x>):
| Element | Status | Note |
Fence tests: <pass/total> MEASURED (network log: .shots/<phase>/…)
Style/static checks: …
Deleted old code: …
Backend deps hit: …
Deviations kept (with reason): …
BROKEN / open: …
Commit: <hash> pushed: yes/no
```

---

## 8. Session management

- If context runs long, finish the current phase to green (or stop cleanly at a sub-step), update §9 with exactly where you stopped and what's next, commit WIP only if tests pass, and tell me to start a new session. A new session starts by reading this file, the spec, and §9.
- Never rely on memory of earlier sessions; §9 is the memory.

---

## 9. Progress log (append-only; newest at bottom)

### Recon

**Frontend map.** Entry `frontend/src/main.tsx` renders `<App/>` (no router of any kind —
confirmed no router package in `package.json` and no route/URL state anywhere; the app
renders `<Library/>` when `work === null`, else the graph shell, purely off React state).
`App.tsx` (765 lines) owns everything: works list, current work, chapter `n`, four
independent client-side view filters (min-degree, background-salience toggle, type
isolation, path-finding), selection, error, delete-confirm. `GraphView.tsx` (417 lines) is
the only Cytoscape init site — one `cytoscape({ container, style: STYLE })` in a mount
effect, `cytoscape.use(cola)` registered at module scope; imperative throughout (refs +
effects, not a wrapper library). `Composer.tsx` (235 lines) is the paste-a-novel ingest/
append UI. `Library.tsx` (100 lines) is the shelf/landing view. `api.ts` / `ontology.ts` /
`types.ts` are thin typed helpers, all already TypeScript (frontend is TS throughout, so
`cytoscape-style.js` ports to `.ts`, per §1).

**Fetching.** `api.ts` → `fetchGraph(slug, n)` GETs `/api/v1/works/{slug}/graph?n={n}`
(server 422s without `n` — reading position is never optional, already true of the old
API). `App.tsx`'s effect re-fetches on every `[work, n]` change: no cache, no
AbortController, one fetch per change — the new build's single-in-flight-request +
payload-cache work (Phase 3) is a genuinely new layer, not a refactor of existing caching.

**Payload shape** (`GraphResponse` in `types.ts`, mirrors `storyweave/api/schemas.py`
exactly): `{ slug, n, elements: { nodes: [{data: GraphNodeData}], edges: [{data:
GraphEdgeData}] } }`. `GraphNodeData` = id/label/type/subtype/importance/
first_seen_chapter/revealed_chapter/extraction_method/evidence_span/properties.
`GraphEdgeData` = id/source/target/relation/tier/first_seen_chapter/revealed_chapter/
extraction_method/evidence_span.

**Live fixtures captured** (MEASURED — hit the running API, not read off schema code) for
the Hollow Crown demo at every chapter → `frontend/tests/fixtures/hollow-crown/
graph-n{1..4}.json`. Growth: 6/5 → 10/9 → 12/12 → 13/13 nodes/edges (matches
SETUP_NOTES.md's prior spot-check). Findings from the real payloads:
- A `Title` node (`"Prince"`, type `Title`) is present from n=2 on — confirms DESIGN_SPEC
  §7.1's "Title never drawn as a node" rule is load-bearing on real data, not hypothetical.
- The Gray Sparrow/Lady Veris pair carries a `RelatedTo` (tier 1) edge AND an `ALIAS`
  (tier 3) edge between the same two node ids — confirms the §7.3 "identity edge absorbs
  the parallel social edge" merge rule is needed for real data, not a hypothetical case.
- `ontology.ts`'s `IDENTITY_RELATIONS` set (SAME_AS/ALIAS/SECRET_IDENTITY/REINCARNATION/
  TRANSMIGRATED_INTO) matches DESIGN_SPEC §7.4's relation-copy table exactly, all five
  present; no missing enum to add.

**Existing frontend tests: none.** No `*.test.*`/`*.spec.*` file exists anywhere under
`frontend/src`, and no test runner (Vitest/Jest/RTL) is configured in `package.json`. Per
the branching instructions: there is nothing to delete or rewrite when a later phase
replaces an old component — noted here so a later phase doesn't go looking for tests that
were never there.

**Start commands** (see SETUP_NOTES.md for the full walkthrough):
```
# Backend (from repo root, light venv)
.\dev.ps1
$env:STORYWEAVE_DB_PATH="storyweave-demo.sqlite"; uvicorn storyweave.api.app:app --port 8000

# Frontend dev server (separate terminal)
cd frontend && npm run dev            # http://localhost:5173

# Screenshot harness (needs both of the above already running)
cd frontend && npm run shoot -- --phase=<id>
cd frontend && npm run test:fence
```

**D1 verdict — quote clause for identity edges: CONFIRMED PRESENT, populated.**
`GraphEdgeData.evidence_span` (schemas.py:186-195) exists and is serialized in the fenced
`/graph` response. Verified live: `n=2`'s `SECRET_IDENTITY` edge carries
`evidence_span: "Wren was Caelum."`; `n=3`'s `ALIAS` edge carries `"the Sparrow and Veris
were one"`; `n=4`'s `TRANSMIGRATED_INTO` edge carries `"an older soul, drowned prince"`.
No fallback needed for the Dossier identity-block quote (DESIGN_SPEC §6.2 point 5) or the
Reveal-card quote (§6.5 point 4).

**D4 verdict — entity aliases list for search: ABSENT as a dedicated field, but the gap is
narrower than it looks.** No `aliases: string[]` field exists anywhere in `schemas.py` or
`types.ts`, and no separate endpoint returns one. However every alias/secret-identity/
reincarnation counterpart is modelled as its OWN node with its own `label` (e.g. "Wren"
and "Prince Caelum" are two distinct nodes joined by a `SECRET_IDENTITY` edge, not one
node with an alias list) — confirmed in the live n=4 fixture. So DESIGN_SPEC §6.3's
"searches name and aliases present in the fenced payload only" is satisfiable by a plain
search over all node labels in the fenced payload, with no new field needed: every name a
reader has learned (including revealed alter egos) is already its own searchable node
label. The D4 fallback ("search names only") is therefore effectively the same as the
full feature here — flagging in case a future novel's data models aliases differently
(e.g. a name-variant list on one node) rather than as separate nodes, which WOULD need the
fallback for real.

### Backend deps hit
- D1 (quote clause): not needed — confirmed present (see verdict above).
- D4 (alias list): running on the fallback (search node labels only), but per the verdict
  above this is observationally equivalent to the full feature for how this backend
  actually models identities. Revisit if a future work's data shows aliases modelled any
  other way.

### Phase reports

## Phase 0 — Recon + verification harness — GREEN
Scope delivered: frontend recon (§9 above); live payload fixtures for the Hollow Crown
demo at n=1..4; D1/D4 verdicts; Playwright installed locally (`@playwright/test` +
`cross-env` as devDependencies) and driven via system Chrome (`channel: "chrome"`) rather
than a Playwright-managed download — the bundled Chromium download timed out repeatedly
against `cdn.playwright.dev` on this network (3 retries, all `ETIMEDOUT`); system Chrome
is already present at the standard Windows path and Playwright supports it natively with
no behavioural difference for this harness. `PLAYWRIGHT_BROWSERS_PATH` still set in
`dev.ps1`/`dev.bat`/both npm scripts pointing at `.local/ms-playwright`, so a bundled
install can proceed into the repo-local dir later if the network allows it, with no script
changes needed. `frontend/scripts/shoot.mjs` (+ `scripts/shots.config.mjs`) — the visual
harness — and `frontend/tests/fence.spec.ts` (+ `tests/fenceHelpers.ts`) — the fence test
skeleton, all 9 rules F1-F9 as `test.fixme` since the chapter/bookmark model doesn't exist
yet — both built and run. Baseline screenshots of the current "constellation" UI at
1440×900 and 1280×720 (library + graph views) captured to `.shots/phase-0/`. §1 file
normalisation: design package confirmed already in `docs/design/`; old `frontend/
DESIGN.md` marked superseded (one-line header, per §1's table). Branching: `main` had
uncommitted environment-setup + design-package files from the prior session pending
review — per your direction, committed + pushed those to `main` first (commit `d995a70`),
confirmed clean, then created and pushed `redesign/codex` from it.

Spec sections covered: §1 (file normalisation), FRONTEND_OVERHAUL §3 (all 7 points).

Visual comparison: N/A this phase (no artboard to compare against yet — these are
baseline "before" shots of the OLD UI, not the redesign).

Fence tests: 0/9 run (all `test.fixme` by design, per §3 point 5) — MEASURED via
`npm run test:fence`: all 9 report as fixme/skipped, exit 0, no browser download
triggered.

Style/static checks: N/A this phase (§4.2/§4.3 checks start Phase 1, once real tokens/
components exist to check).

Deleted old code: none (recon-only phase; §1 also did not require deleting anything).

Backend deps hit: see above (D1 clear, D4 fallback is a non-issue for this backend's data
model).

Deviations kept (with reason):
- Chromium bundled-browser install skipped in favour of system Chrome via `channel:
  "chrome"` — network-blocked download, documented above, fully reversible (no code path
  depends on the browser being Playwright-managed vs. system-installed).
- `frontend/src/styles/tokens.css`, `frontend/src/graph/codexStyle.ts`, and
  `frontend/src/assets/mural-codex.svg` (the "live" copies §1's table lists) were NOT
  created this phase — only the reference copies in `docs/design/` exist so far. Phase 1
  wires tokens.css globally and Phase 5 ports the Cytoscape style; creating unused copies
  in `frontend/src/` now would be scaffolding those phases early (§2 rule 8/"one phase at
  a time"), and Phase 0's own constraint is explicitly "no visual or behavioural changes."

BROKEN / open: none.

Commit: (pending — see below) pushed: pending.

MEASURED: pytest 124 passed / 6 skipped (matches SETUP_NOTES.md's baseline, zero
regression). `npm run build` (`tsc -b && vite build`) clean, one pre-existing chunk-size
warning (unrelated, already known). `npm run shoot -- --phase=0`: 4/4 shots OK, zero
non-benign console errors. `npm run test:fence`: 9/9 fixme, exit 0.
