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
14. **Session log.** Every session appends an entry to `docs/design/SESSION_LOG.md` before its final commit, including sessions that stop mid-phase. A cold-start session reads the latest SESSION_LOG entry right after §9 of this file.
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

- If context runs long, finish the current phase to green (or stop cleanly at a sub-step), update §9 with exactly where you stopped and what's next, commit WIP only if tests pass, and tell me to start a new session. A new session starts by reading this file, the spec, §9, and then the latest entry of `docs/design/SESSION_LOG.md`.
- Never rely on memory of earlier sessions; §9 and SESSION_LOG.md are the memory.

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

## Phase 1 — Tokens & typography — GREEN

Scope delivered: `@fontsource/pirata-one`, `@fontsource/eb-garamond` (400/500/600/
400-italic), `@fontsource/alegreya-sans` (400/500/700) installed; old `@fontsource/
spectral`/`ibm-plex-sans`/`ibm-plex-mono` uninstalled. `tokens.css` copied to
`frontend/src/styles/tokens.css` (mural `url()` path fixed to `../assets/
mural-codex.svg`; `mural-codex.svg` copied to `frontend/src/assets/`) and imported once,
globally, in `main.tsx`, ahead of the old `styles.css` — the `.mural`/`.vignette` classes
exist in the stylesheet but nothing mounts them yet (R2). Old global fonts + the old
palette `:root` block removed from `styles.css` (old screens now degrade — see comparison
below). Five primitives built, tokens-only, each in its own folder per §6: `Button`
(primary/outline/quiet/icon × hover/focus/disabled), `Tabs`, `Input`, `Ornament` (§4.4
rule), and the 9 required icons (`chevron-left`, `chevron-right`, `close`, `lock`,
`arch-door`, `eye`, `plus`, `minus`, `search`) as inline stroke SVGs (1.5px, square caps,
`currentColor`). Hidden dev route `#/_type` (`frontend/src/dev/TypeScale.tsx`) renders the
full type scale (Display only ≥28px, per the hard rule), every color token as a swatch
(value read live via `getComputedStyle`, never hardcoded — so the page can't drift out of
sync with tokens.css), every primitive in its default/disabled states, and all 9 icons at
16px and 24px — wired into `main.tsx` behind the smallest possible hash check
(`window.location.hash === "#/_type"`, no listener, no re-render on hash change — R2
replaces this with the real router). `npm run lint:design` added (raw-hex, `var(--accent`,
literal-font-family checks per §4.3) with two separate, commented allow-lists (legacy
files pending removal by phase; red-permitted files). `npm run test:style` added — the
five §4.2 computed-style assertions, run against `#/_type`.

Spec sections covered: §2 (P2 red discipline, P6/P7/P8), §3 (keep/discard list — old
fonts/palette/gold now gone), §4.1–§4.4 (tokens, typography, spacing/radius/borders,
ornament/icons), §10 (Button, Tabs).

Visual comparison (`#/_type`, MEASURED — screenshots at 1440×900 and 1280×720, inspected;
artboards 1–2 used as type/colour reference since there's no `#/_type` artboard):
| Element | Status | Note |
|---|---|---|
| Display (Pirata One) blackletter, H1-scale | matches | Renders correctly at 30/36/44/60/72/96; correctly absent below 28px |
| Body (EB Garamond) | matches | Serif, italic-capable family loads; roman used in scale samples |
| UI (Alegreya Sans) | matches | Sans, used for buttons/tabs/labels/captions |
| Color tokens (14, incl. `--scrim`) | matches | All render with correct hue/opacity vs. tokens.css; `--accent` reads as rubric red, `--accent-hi`/`--accent-soft` as lighter/softer variants |
| Button primary/outline/quiet/icon | matches | Fill+on-ink+700 / 1px ink border / text-only / 44×44 glyph-only; radius 0 confirmed (style test) |
| Button disabled | matches | `--faint` per spec |
| Tabs | matches | 1px underline on active, `--dim` inactive |
| Ornament rule | matches | Thin `--line` hairline + centred rotated-square lozenge |
| Icons (9/9 required glyphs) | matches | Square caps, `currentColor`, no fill packs, 16/24px both shown |
| Red discipline | matches | `--accent` used only inside the token-swatch demo (allow-listed, documented reason); no primitive defaults to accent |

Old-screen "expected-degraded" record (`.shots/phase-1/library-expected-degraded@*`,
`graph-expected-degraded@*` — MEASURED, not something fixed): degradation is real but
**subtler than "broken"**, for two structural reasons, both ASSERTED from reading the
cascade rather than guessed: (1) `styles.css` and the new `tokens.css` happen to share
the custom-property names `--ink` and `--line`, so old rules using those two names
silently pick up the new (visually close) Codex values instead of going invalid; (2) the
old Cytoscape canvas (`GraphView.tsx`) never used CSS variables at all — its colors are
hardcoded JS hex constants in `ontology.ts` — so the graph canvas itself is untouched by
this phase and looks identical to before. What DID visibly change: the old gold
"*Weave*" wordmark accent and the focus-ring color (`--reveal`, fully removed, no Codex
equivalent) fall back to inherited/initial instead of gold. This is compliant with the
phase's own instruction ("old screens will look wrong ... do not restyle") — it doesn't
mandate a specific degree of wrongness, and I did not patch it.

Fence tests: 0/9 run, 9/9 still `test.fixme` — MEASURED (`npm run test:fence`, exit 0,
unchanged from R0 — this phase touches no chapter/bookmark logic).

Style/static checks: MEASURED — `npm run lint:design`: 23 files checked, 0 failures
(2 legacy-allow-listed, 1 red-permitted). `npm run test:style`: 5/5 passed (Pirata One
never <28px; no uppercase+letter-spacing; radius 0 except `[data-round]`; all three fonts
`document.fonts.check()` true; no horizontal scroll at 1280×720).

Deleted old code: none outright — the old `:root` palette/font block in `styles.css` was
removed (not deleted-as-a-file; the file itself still serves the not-yet-replaced old
screens, per R4 the file itself is deleted only when the screens it styles are replaced).

Backend deps hit: none (no backend interaction this phase).

Deviations kept (with reason):
- A real bug found and fixed during this phase (not a deviation, noting for the record):
  `#/_type`'s color-token swatch container was originally named `.swatch`, colliding with
  an unrelated pre-existing `.swatch` class in old `styles.css` (a 9px legend dot,
  `border-radius: 50%`) — both stylesheets load globally with no CSS Modules scoping, so
  the old rule was silently clobbering the new page. Caught by the `test:style`
  border-radius assertion (14 unexpected `50%` radii), fixed by renaming to a `tok-`
  prefixed namespace. Left as a cautionary note for later phases: watch for collisions
  with the old app's class names until `styles.css` is fully retired (R8).
- `shoot.mjs`/`shots.config.mjs` refactored mid-phase: the harness originally did one
  shared `page.goto(BASE_URL)` before every shot; adding the `#/_type` hash-route shot
  exposed that a same-origin URL differing only in the fragment does NOT trigger a full
  page reload, so a shared pre-navigation left a later hash-route shot on a stale,
  never-re-rendered page. Fixed by making every shot own its full navigation
  (`run(page, baseUrl)`); verified R0's shots (`--phase=0`) still pass unchanged after the
  refactor.

BROKEN / open: none.

Commit: (pending — see below) pushed: pending.

MEASURED (regression guards): pytest 124 passed / 6 skipped (unchanged). `npm run build`
clean (one pre-existing chunk-size warning). `npm run typecheck` clean.

MEASURED (old fonts/palette gone — grep evidence):
```
$ grep -rn "Spectral\|IBM Plex" frontend/src/
src/GraphView.tsx:60:      "font-family": "IBM Plex Sans, system-ui, sans-serif",
src/GraphView.tsx:86:      "font-family": "IBM Plex Sans, system-ui, sans-serif",
```
The only surviving matches are the two hardcoded Cytoscape-stylesheet literals in
`GraphView.tsx` (the exempt "Cytoscape style module," §2 rule 6 — Phase 5 replaces this
file wholesale). The font is no longer loaded (its `@fontsource` import is gone from
`main.tsx`), so these two lines are now dead references that silently fall through to
`system-ui, sans-serif` — not a live font-loading path.
```
$ grep -rn -- "--ground:\|--surface:\|--reveal:" frontend/src/
(no matches)
```
Old palette variable *definitions* are fully gone (some old rules still *reference*
`var(--ink)`/`var(--line)` by name, but those now resolve against the NEW tokens.css
definitions of the same names — see the degradation note above).

Next: **R2 — Shell** (router, mural + vignette mount, three-column layouts, theme
strings). Same model recommendation as before (Sonnet 5) — R2 is layout/structural work
with a clear screenshot-verifiable done-when, not a phase needing extra design judgment.

## Phase 2 — Shell — GREEN

Scope delivered: hand-rolled hash router (`router/useHashRoute.ts` + `router/
AppRouter.tsx`) covering all six routes — `#/` (landing), `#/work/:slug/entity/:id`
(Dossier), `#/work/:slug/web?focus=:id` (Stemma), `#/work/:slug/chronicle` (Chronicle),
`#/_type` (now a real route, replacing R1's hash hack), `#/_legacy` (the entire old app).
`#/work/:slug` with no entity resolves to `entity/_pending` and normalises the visible URL
via `history.replaceState` (no spurious history entry). Unknown routes fall through to
landing. The bookmark never appears in any URL — nothing in R2 reads or writes a chapter
number at all yet (that's R3). `LegacyRoute.tsx` mounts `<App/>` unchanged, loading
`styles.css` lazily (dynamic `import()`) only when this route actually renders — confirmed
in the production build, which now emits a separate `styles-*.css` chunk. Mural + vignette
mounted as fixed background layers in `CodexApp.tsx`, using tokens.css's own global
`.mural`/`.vignette` classes (§4.6 rules 1-2); Stemma's canvas region carries the global
`web-canvas-mask` class (rule 3); rails/panels/header bars use `--panel`, main/chart
regions use solid `--bg` (rule 4 and the P6 "not under body text" clause). Four screen
shells built with real geometry (Landing §6.1, Dossier §6.2, Stemma §6.3, Chronicle §6.4)
and placeholder content boxes — no fake story data, only dev-marker text naming which
phase owns each region. Tabs (R1 primitive) route between the three in-work screens and
reflect the active route. Theme strings object (`codex/theme.ts`) with all 10 §12 keys
plus the two additional tab-label keys the table doesn't spell out; used for real in
Landing's kicker/H1 (P2-permitted accent) and the tabs, the rest defined and ready for
the phases that render them. `useWorkTitle` hook reads the real `/works` endpoint and
resolves the current work's title in Dossier/Stemma/Chronicle's rail — the first real
data on screen; nothing else fetches.

Spec sections covered: §4.3 (spacing/radii/borders), §4.6 (mural placement rules 1/2/3/4),
§5 (routes, no-bookmark-in-URL), §6.1-§6.4 (geometry only), §12 (theme strings).

Visual comparison (geometry only — content is placeholder; MEASURED via
`npm run test:geometry`, `getComputedStyle`/`boundingBox`, plus screenshots at 1440×900
and 1280×720, inspected against artboards 1-4):
| Element | Status | Note |
|---|---|---|
| Dossier rail width | matches | 290px @1440, 260px @1280 (breakpoint) |
| Dossier right panel width | matches | 400px @1440, 320px @1280 |
| Stemma rail width | matches | 290px @1440, 260px @1280 |
| Stemma right panel width | matches | 350px @1440, 320px @1280 |
| Chronicle header bar height | matches | 76px, no left rail (correct — spec has none) |
| Chronicle right panel width | matches | 330px at both widths — tokens.css has no 1280-1439 override for `--rail-right-chronicle` (only `--rail-left`/`--rail-right-dossier`/`--rail-right-web` are overridden); used as authored, not silently "fixed" |
| Landing left column / gap | matches | 580px / 64px |
| Mural: fixed, non-interactive, z-index 0 | matches | `getComputedStyle` confirms `position:fixed; pointer-events:none; z-index:0` |
| Stemma canvas centre mask | matches | `web-canvas-mask` class present; visible as a faint radial fade at the canvas edges in the screenshot, solid centre |
| No horizontal scroll @1280×720 | matches | landing/dossier/stemma/chronicle all pass |
| Tabs active-state reflects route | matches | underline on the correct tab per screenshot, for all three in-work screens |
| Red discipline | matches | `--accent` only in Landing's kicker (spec-permitted) and `#/_type`'s swatch demo (R1 allow-list) |

Fence tests: 0/9 run, 9/9 still `test.fixme`, unchanged (`npm run test:fence`, MEASURED,
exit 0) — R2 touches no chapter/bookmark logic.

Style/static checks: MEASURED. `npm run test:style`: 5/5 passed, unchanged from R1.
`npm run test:geometry` (new, R2): 13/13 passed — the 4 screens' rail/panel/header
dimensions at both breakpoints, mural/vignette computed-style, the Stemma mask class,
`#/_legacy`'s interaction check (library → click a work → graph canvas → scrubber
visible), and no-horizontal-scroll for all 4 new screens. `npm run lint:design`: 39 files
checked, 0 failures (2 legacy-allow-listed, 2 red-permitted — added `codex/Landing/
Landing.module.css` for the spec-permitted kicker accent) — includes the new R2 collision
check (plain, non-module CSS only; `.module.css` files are exempt since Vite hashes their
class names at build time, so a shared source-level name can never collide at runtime —
documented in the script).

Deleted old code: none this phase (the legacy app moves behind `#/_legacy`, it isn't
deleted — R9 deletes it).

Backend deps hit: none (only reused the already-existing, unchanged `fetchWorks()`).

Deviations kept (with reason):
- **Corrected an R1 assumption, not a new deviation**: the R1 report guessed `styles.css`
  and `ontology.ts`'s old color constants would shrink piecemeal across R2/R4/R5/R7/R8.
  Building `#/_legacy` this phase made the real mechanism concrete — they're reachable
  ONLY via that route from R2 on (no longer globally imported), so they don't shrink at
  all until R9 deletes the legacy route wholesale. `lint-design.mjs`'s `LEGACY_FILES`
  entries and comments updated to say R9, with the correction noted inline.
- A real bug found and fixed during this phase (not a deviation, noting for the record):
  the new R2 lint:design collision check initially flagged `Button.css`/`Ornament.css`/
  `Tabs.css`/`tokens.css` for "colliding" on class names `md`/`css` — the regex was
  matching `.md`/`.css` inside comment text like "DESIGN_SPEC.md" and "tokens.css".
  Fixed by stripping `/* ... */` comments before extracting class selectors.
- Phase 0/1's `library`/`graph`/`*-expected-degraded` shot configs now fail if re-run,
  because they navigate to the bare `baseUrl`, which pre-R2 resolved to the old app and
  now correctly resolves to the new Landing route. This is R2 working as intended, not a
  regression — documented inline in `shots.config.mjs` rather than rewritten to keep
  "passing" against a URL contract that no longer applies. Phase 2's own `legacy` shot
  (at `#/_legacy`) is the up-to-date equivalent, and the geometry test suite's `#/_legacy`
  interaction check covers the same ground as an assertion.

BROKEN / open: none.

MEASURED (regression guards): pytest 124 passed / 6 skipped (unchanged). `npm run build`
clean — confirms `styles.css` now code-splits into its own chunk, loaded only for
`#/_legacy`. `npm run typecheck` clean.

Commit: (pending — see below) pushed: pending.

Next: **R3 — Chapter model + fence** (the most important correctness phase: bookmark
state, `ChapterDialog`, fetch layer with single in-flight + AbortController, payload
cache with purge-on-back, forward/backward flows, un-fixme F1/F2/F3/F5 and the aborted/
error-banner tests with real network logs attached). Recommend staying on Sonnet 5 for
the mechanical plumbing (fetch layer, cache, dialog), but this is the phase where
correctness bugs are most costly (it's the project's core engineering claim) — if you
want an extra pass of scrutiny on the fence logic specifically, an Opus-driven review
after the Sonnet build (rather than building on Opus outright) would be the efficient way
to get that without slowing the whole phase down.

## Phase 3 — Chapter model + fence — GREEN

Scope delivered: `codex/chapter/` — `bookmarkStore.ts` (per-work `storyweave:bookmark:
<slug>`, default 1 on first visit, stored value validated on every read: integer in
1..chapter_count else reset to 1 and re-written), `ChapterProvider.tsx` (one instance per
open work, keyed by slug in `CodexApp`, shared across all three tabs: the fetch layer for
`/api/v1/works/{slug}/graph?n=` with exactly one request in flight, AbortController on
every new confirm **and** a request token so a late-resolving superseded response can never
reach state; in-memory cache holding chapters ≤ bookmark only, purged synchronously on
any backward move before any await; forward flow keeps old data under the wash and
commits bookmark+localStorage only on success; backward flow commits at once; §6.7 error
rule), `ChapterListCompact` (≤5 rows, prev-2 / bookmark / exactly one sealed row of fixed
44px, "of N" only, "Change chapter" button), `ChapterDialog` (digits-only, clamp with
inline "There are only N chapters.", zero network while typing, context list with past
rows filling the input, "For long serials" blocks-of-100 fallback with the confirm-before-
fill step, focus trap, Esc, Enter-on-valid, Set bookmark / Cancel, footnote),
`ChapterChrome` (40% wash, error banner with Try again, forward/backward toasts, `[` / `]`
keys ignored inside inputs and while the dialog is open), `roman.ts`; `graph/diff.ts`
(pure: new nodes / edges / identity edges). Theme strings for all of the above added to
`codex/theme.ts`. Vitest 2.x added as a dev dep (Vitest 5 peers on Vite 6+; not
upgrading the build tool mid-phase) with `npm run test:unit`. Session log created
(`docs/design/SESSION_LOG.md`, rule R6 / §2 rule 14). Phase 0/1 shot configs retargeted at
`#/_legacy`/`#/_type` so every shot config in the repo passes again.

Spec sections covered: §5 (bookmark local, never in URL), §6.2 item 2, §6.6 complete,
§6.7 error rule, §8.1 (minus reveal overlay → R6), §8.5 `[`/`]`, §9.1 F1/F2/F3/F5.

Visual comparison (MEASURED — `.shots/phase-3/*` at 1440×900 and 1280×720, inspected
against artboards 2 and 6 rendered via Chrome to `.shots/artboards/`; three fix loops
used on the dialog, one on the rail):
| Element | Status | Note |
|---|---|---|
| Rail "Where are you?" label + rows (artboard 2) | matches | 2 read / bookmark / 1 sealed; single hairline frame, rows stacked; bookmark row `--ink` fill + 600; sealed row `--deep` + `--faint` + lock glyph |
| Row height | matches (44px) | artboard ≈42px; 44 is the spec's target size, kept |
| "of 4" on the label row | deviates (additive) | not drawn on the artboard, but §6.2 permits "of N" and it's the only place the book length appears |
| "Change chapter" button | matches | full width, 44px, 1px `--ink` outline |
| Dialog frame (artboard 6) | matches | 640px, `--bg`, 1px `--faint`, 72% scrim |
| Title Display 42 + close 44×44 | matches | |
| "I have finished chapter [ 3 ] of 4" — 110×64 input, Display 40 | matches | selection highlight re-coloured to tokens (was browser blue) |
| Helper copy | matches | |
| Context list: 2 prev / bookmark (`--raise`, red "current bookmark") / sealed | matches | |
| "For long serials" | deviates | artboard shows explanatory prose; spec §6.6 item 5 says list the arcs or the blocks-of-100 fallback → shows "Chapters 1–4" chip with confirm-before-fill (spec > artboard) |
| Set bookmark (52px, primary, wide) + Cancel (outline) | matches | |
| Footnote | matches | |
| Invalid state | matches spec | "There are only 4 chapters." inline; Set bookmark disabled |
| Loading wash after confirm | matches spec | 40% `--bg` over old data + loading copy; no spinner |
| Error banner | matches spec copy | "Couldn't load Chapter IV — still showing Chapter III" + Try again; solid `--bg` |
| Forward / backward toasts | matches spec copy | bottom-centre, UI 14, 4s |

Fence tests: **25/25 passed, 5 fixme** MEASURED (`npm run test:fence`; every network
assertion attaches its `/graph` request log as `graph-requests` in `test-results/`). Active:
F1 ×5 (default visit, dialog forward, `]` fetches nothing, typing incl. 2000 + Enter,
rapid double confirm), F2/F3, F5 ×2, §8.1 ×2 (confirm-then-back-before-resolve, slow
older response dropped), §6.7 ×2 (500 keeps data/bookmark; Try again re-requests only
the failed chapter and any move clears it), persistence across reload, tampered storage
×6 (`0`, `-3`, `999`, `abc`, `2.5`, empty), tab switch mid-fetch, browser back mid-fetch,
unknown slug → zero requests, keys inert in inputs, dialog fill/Esc, focus trap. Fixme,
each named with its activating phase: F4 (R4/R8), F6 (arc names — inactive while D6 is
absent), F7 (R7), F8 (R4), F9 (R8). Unit: 11/11 (`roman`, `diffGraphs` on the real
n=1..4 fixtures, `validateBookmark`).

Adversarial review (Step 3) — paths by which chapter > bookmark could be requested,
cached, rendered or hinted, each → the test that closes it:
- tampered/hand-edited storage → validateBookmark (unit) + 6 Playwright variants.
- typing in the dialog / Enter on invalid / out-of-range confirm → "no request while
  typing"; `requestChapter` re-validates 1..N independently of the dialog.
- `]` spam / `]` + keys with dialog open → "`]` fetches nothing", "keys never fire inside
  inputs" (dialog-open guard + typing-target guard).
- rapid double confirm, confirm-then-back, slow older response → three §8.1 tests (token
  guard is what closes the late-resolve gap; abort alone would not).
- error retry → banner test: only the failed (reader-confirmed) chapter is re-requested;
  any move clears the banner so a stale retry can't fire later.
- tab switch / browser back during a fetch → both tested; provider is keyed by slug and
  aborts + invalidates on unmount.
- multiple works → provider remount per slug (fresh cache); unknown slug → chapter_count
  unknown → dialog refuses to open, zero requests (found live: `]` opened an inert dialog
  for an unknown work — fixed by gating `openDialog` on chapter_count).
- cache above bookmark → set only in `load` after the token check and consumed by
  `commit` in the same microtask chain; purge on backward runs before any await (F5 test).
- hints → F2/F3 test: only "of N" and the immediately-next sealed numeral appear.
- other fetch sites → grep: the only other `graph` fetch is legacy `App.tsx`, reachable
  only at `#/_legacy`.
Nothing left open → no BROKEN.

Style/static checks: MEASURED. lint:design 52 files clean (red-permitted now 3: the
dialog's "current bookmark" marker); test:style 5/5; test:geometry 13/13; typecheck +
build clean; shoot phases 0/1/2/3 all pass (4 + 6 + 12 + 20 shots), zero console errors.
`shoot.mjs` gained a per-shot `expectedConsoleErrors` (the error-banner shot injects a 500
and Chrome logs it itself) — declared per shot, never a global allow.

Deleted old code: R2's standalone fetch-and-find `useWorkTitle` body replaced by a
context read (the file stays, one function, same name); nothing else replaced this phase.

Backend deps hit: D3 (chapter_count from `/works`) used. D6 (arc config) absent →
blocks-of-100 fallback, as specified.

Deviations kept (with reason):
- Backward move whose (uncached) fetch fails: shows "Couldn't load Chapter II." with NO
  data, rather than §6.7's "keep previous data" — the previous data is from a HIGHER
  chapter than the new bookmark, so keeping it on screen would display beyond the
  bookmark. Safer than literal; documented in `ChapterProvider`.
- `[`/`]` are a window listener with a typing-target + dialog-open guard rather than a
  handler on the root element: after a click, focus sits on `<body>`, which is outside
  any root element, so a root-scoped handler would silently never fire.
- Two real test-harness bugs fixed on the way: `recordGraphRequests` used
  `includes("/graph")`, which also matched Vite serving `src/graph/diff.ts` — anchored to
  the API route; and my first "slow older response" test pressed `[` at chapter 1 (a
  no-op) so it proved nothing — rewritten to start from chapter 2. Both would have made
  fence evidence wrong in opposite directions.

BROKEN / open: none.

Interview-defence note: the frontend fence is defence-in-depth, not the seal. The seal
is `query/fence.py` — a `WHERE revealed_chapter <= :n` applied at the SQL/index level, so
a row past the bookmark never leaves the server regardless of what any client does. The
UI layer's job is different: it guarantees the client never *asks* for more than the
reader confirmed (F1), never keeps a payload it shouldn't (F5), never renders a response
the reader has since moved away from (token + abort), and never hints at what's beyond
(F2/F3). That closes the UX-level leaks — prefetching, stale renders, cached ghosts —
that a correct server fence cannot see, while never being something the server relies on.

MEASURED (regression guards): pytest 124 passed / 6 skipped (unchanged).

Commit: (see SESSION_LOG.md Session 4) pushed: yes.

Next: **R4 — Dossier** (rail cast list with degree sort + "changed" tags via
`graph/diff` (F8), H1/lede/ornament, identity blocks with the D1 quote, ties grid, fence
line, concentric ego graph, entity-not-present state, default entity = highest-degree
person). Model: Sonnet 5 is fine — it's layout + view-model work over a fence that is
now tested; the F8 diff is already a unit-tested pure function.

## Phase 4 — Dossier — GREEN

Scope delivered:
- **Step 0 (R3 follow-up).** Backward-fetch failure now shows the §6.7 error CARD ("The
  archive didn't answer." + Try again) in the main column instead of a banner; the
  bookmark commits to the lower chapter, cache is purged, DOM holds no higher-chapter
  data, Try again re-requests exactly that chapter. Behaviour was already the safe one
  (R3 report); the card + test are new. Banner is now only for "still showing Chapter N".
- **Step 1 (shared graph foundation).** `graph/viewModel.ts` — pure `(payload, options)
  → {nodes, edges, alsoMentioned, byId}`: §7.1 kind mapping (Title never a node; Concept/
  Event → "also mentioned"), degree from merged fenced edges, §7.3 parallel merge
  (identity absorbs social in either payload order; other parallels → one edge with a
  relation list, earliest chapter kept), §8.4 quote-less identity edge dropped with an
  injectable `warn` (console.warn by default), §7.4 copy table `IDENTITY_COPY` checked
  against `ontology.ts`'s five identity enums — **no enum was missing, nothing added**
  (SAME_AS shares ALIAS's pattern per the spec table). Helpers: `tiesOf`, `sortCast`,
  `principalOf`, `countWords`, `initialOf`, `tieLabel`. `graph/codexStyle.ts` ported from
  `docs/design/cytoscape-style.js` (TS, typed loosely once at the export because
  Cytoscape's typings reject `mapData` strings/underlay-*), with the tokens.css mirror
  header; now the single lint-exempt Cytoscape file (GraphView.tsx moved to LEGACY_FILES).
- **Step 2 (Dossier, §6.2 complete).** Rail: wordmark → landing, title, R3 chapter block,
  `CastList` (degree → first appearance → name; selected row `--raise` + 2px `--ink` rule +
  600; "changed" tags; Orders & Houses / Places & Relics inline clickable; top 12 + "All N
  people →" → searchable full list; scrolls independently). Main: `EntityMain` — H1
  Display 96 (80 at 1280–1439 via media query), lede from the theme template with words to
  twenty (+ a `ledeOne` singular, "one bond recorded"), one ornament, identity blocks
  newest-first (kicker, sentence with the other name as an italic `--accent-hi` link, curly
  evidence quote, plain "Chapter N" since D5 is absent), ties grid 2-col sorted by revealed
  chapter then name with 12 + "All N ties →", "Also mentioned" line, fence line pinned at
  the bottom (arch-door glyph with the §9.2 tooltip as `title`). Right panel: "The Stemma
  of X" + "open full →" (routes to `#/work/:slug/web?focus=:id`), `EgoGraph` (Cytoscape
  `concentric`, codexStyle, focus disk with initial, 1-hop `.near`, 2-hop `.far`; click →
  dossier; drawn ids mirrored to `data-nodes`/`data-edges` for the DOM tests), legend.
  States: skeleton (H1 bar + 3 bars), not-present card with "Go to the principal
  character", error card. Routing: `#/work/:slug` → principal via `location.replace` (no
  history entry, hashchange still fires). `codex/states/StateCard` is the shared §6.7 card.
- **Chapter model:** `prevData` (n−1) added to `ChapterProvider` — fetched only after the
  bookmark's own payload commits, through the same cache, with its own AbortController
  (never touches the main request or the bookmark). F8 is therefore satisfied by
  construction: the tags diff `data` against `prevData`, both fenced.
- `tests/fixtures/synthetic-100.json` (+ `make-synthetic.mjs`, seeded, reproducible):
  101 entities / 154 edges / 5 quoted identity edges + 1 deliberately quote-less one;
  served only via route interception with a fake server fence. R5 reuses it.

Spec sections covered: §2 P1/P3/P5/P7/P8, §6.2 all items, §6.7 (loading / not-present /
error cards), §7.1–§7.4, §8.4, §9.1 F4 (dossier) + F8, §9.2, §12.

Backend data note (frozen, not changed): at n=4 the Hollow Crown payload REPLACES Wren→
Caelum's `SECRET_IDENTITY` (e12, revealed 2) with `TRANSMIGRATED_INTO` (e14, revealed 4)
— e12 is absent from the n=4 response. So Wren's chapter-4 dossier shows one
transmigration block, not two blocks, and the chapter-4 "changed" tags mark Wren + Caelum.
The DOM tests assert exactly that, from the fixtures.

Visual comparison (artboard 2, MEASURED — `.shots/phase-4/*` at 1440×900 and 1280×720,
14 real-data shots + 2 synthetic, inspected; one fix loop for the rail scroll clip, one for
the ego cap, one for the lede singular):
| Element | Status | Note |
|---|---|---|
| Rail: wordmark, title, chapter block | matches | unchanged from R3 |
| Dramatis Personae header + hairline | matches | Body 17 `--dim` |
| People rows, Body 19, degree sort | matches | Wren first (degree 4) |
| Selected row (`--raise`, 2px `--ink` rule, 600) | matches | |
| "changed" tag, italic `--accent` | matches | ch2: Wren (identity) + 3 new; ch3: Sparrow, Veris; ch4: Wren, Caelum; ch1: none |
| Orders & Houses / Places & Relics inline | matches | `·`-separated, `--dim`, clickable |
| Rail scrolls when long | matches (after fix) | first render clipped the groups; `.cast{flex:1 1 auto}` |
| Section label + tabs row | matches | |
| H1 Display 96 / 80 @1280 | matches | measured via the two shots |
| Lede italic Body 22 | matches | "first named in Chapter I · four bonds recorded" |
| Ornament 480px, once | matches | |
| Identity block: eye 44px `--accent`, kicker, sentence 34px, quote 21px ≤540px | matches | quote is the real `evidence_span` ("Wren was Caelum.") |
| "Show it in the chapter →" | deviates (spec fallback) | D5 absent → plain "Chapter II" text, per §6.2 item 5 |
| Ties grid 2-col, name 21 / meta 13, hairline | matches | labels are the real relations ("in", "owns", "has ability"; artboard's "carries" is illustrative) |
| Fence line: rule — glyph — copy — rule | matches | tooltip on hover (native `title`) |
| Right panel title + "open full →" | matches | |
| Ego graph: focus disk with initial, ring, 2-hop faint, red identity edge | matches | 2-hop ring dropped when the ego set would exceed 40 nodes (synthetic hub) — labels stayed legible |
| Legend line UI 13 | matches | |
| Red only in: kicker, other-name, changed tag, ego identity edge | matches | Dunmore's dossier (no identity) shows red only on the faint 2-hop Wren–Caelum edge |
| Pirata One ≥ 28px | matches | H1 96/80, state headline 36, novel title 32; test:style 5/5 |
| No mural under body text | matches | main is solid `--bg` |
| Not-present card (Veris @2) | matches spec | neutral copy; never names her |
| Skeleton | matches spec | H1 bar + 3 bars, no spinner |

Fence tests: **27/27 passed, 4 fixme** MEASURED (`npm run test:fence`, logs attached).
Newly active: F4 (dossier variant) and F8. Remaining fixme, named by phase: F4 search
(R8), F6 (inactive while D6 absent), F7 (R7), F9 (R8). Three R3 expectations updated
because the model now legitimately fetches n−1 after a commit (`[3,2]` instead of `[3]`,
etc.) — each still asserts nothing above the bookmark.
Dossier E2E: **6/6** MEASURED (`npm run test:dossier`): the 1→2→3→4→2 walk asserts,
against an independent re-derivation from the R0 fixtures, that identity blocks, ties,
cast, ego nodes AND ego edges, and "changed" tags equal the fenced payload at every step
and that requests are only n / n−1; Veris–Sparrow block present at 3 / card at 2 with
F4 copy and zero old data in the DOM; principal redirect; Step 0 backward failure;
skeleton; synthetic-100 cast overflow (12 → "All 70 people →" → search), ties overflow
(12 → "All 21 ties →"), exactly one distinct `console.warn` for the quote-less edge.
Unit: **25/25** (`viewModel` every rule incl. Title exclusion and identity-absorbs-social
in both orders, degree, cast sort, ties, copy table vs ontology, count words, initials).

Style/static checks: MEASURED — lint:design 61 files clean (red-permitted 4: +
`Dossier.module.css`; legacy 3: + `GraphView.tsx`); test:style 5/5; test:geometry 13/13;
typecheck + build clean; shoot phases 0–4 all pass (4+6+12+20+16 shots), zero console
errors (the synthetic `console.warn` is a warning, not an error, and is asserted only in
the test that provokes it).

Deleted old code: none this phase (R2's Dossier placeholder boxes replaced in place).

Backend deps hit: D1 quote (present, used), D3 chapter_count (used), D4 alias search →
label search over the fenced payload (equivalent per R0), D5 chapter link → absent, plain
text. D6 still absent.

Deviations kept (with reason):
- Identity sentence is always in source→target order with the *other* endpoint linked
  (§7.4 direction lives in the copy): on Prince Caelum's dossier it reads "Wren now lives
  on as *Prince Caelum*." with Wren as the link — correct direction, entity not first.
- "changed" tags are empty at chapter 1 (no n−1 exists; tagging the whole cast would
  say nothing). At every later chapter they are exactly F8's diff.
- Ego graph caps the 2-hop ring at 40 total nodes (see table). ASSERTED-acceptable:
  even 1-hop labels fade for a 21-neighbour hub at panel size (`min-zoomed-font-size`),
  which is §7.2's intended behaviour, not a bug.
- Fence-glyph tooltip is the native `title` attribute rather than a custom popover —
  the copy is the spec's; R9 polish can restyle it if wanted.

BROKEN / open: none.

MEASURED (regression guards): pytest 124 passed / 6 skipped (unchanged).

Commit: (see SESSION_LOG.md Session 5) pushed: yes.

Next: **R5 — The Stemma** (port is done; build the full-graph screen: cola physics
§7.6, focus mode §8.3, principal filter + org folding badge, zoom tiers §7.5, selection
panel, fenced search, centre mask; the synthetic-100 default-fit label-overlap screenshot).
The view model, style and fixture all exist now, so R5 is mostly canvas interaction work.
Model: Sonnet 5 is fine.

## Phase 5 — The Stemma — GREEN

Scope delivered:
- `graph/stemmaModel.ts` (pure, unit-tested): `visibleGraph` (Show checkboxes; Cast size
  Principal = degree ≥ 2 OR identity endpoint OR the focus; hidden organisation members
  fold into their org as a `+N` count), `focusSet` (1/2 steps), `neighboursOf` (arrow-key
  order), `zoomTier` + `labelVisible` (§7.5), `minorLabelIds`/`labelRank`/`declutterLabels`
  (label rules, below), `searchNames` (fenced labels only), `nodeSize` (§7.1 clamp).
- `graph/codexStyle.ts` extended: `data(size)`/`data(sizeFar)` (JS-computed §7.1 sizes;
  20% shrink at the far tier), `display` label (org badge), `.tier-close` full-ink labels
  (+ the focus initial stays `--on-ink`), `.kbd-ring`, `.label-minor`/`.label-deferred`,
  far-tier identity endpoints exempt from `min-zoomed-font-size`; `colaOptions(reduced,
  nodeCount)` — see deviations.
- `graph/cyRegistry.ts`: dev-only `window.__storyweaveCy` {instances, layouts, created,
  stemma}. Both canvases (Stemma + R4's ego graph) register; the Stemma exposes its
  instance so tests read drawn ids and label boxes. Never rendered in the UI.
- `codex/Stemma/StemmaCanvas.tsx`: one Cytoscape instance per mount, one cola burst at a
  time, both destroyed on unmount (tab switch / work switch unmount it). Diff-applies the
  visible graph (new nodes seeded on a ring, positions kept across chapter/filter
  changes), focus/preview/selected/kbd classes, tiers on `zoom`, camera fit on
  `layoutstop` (never mid-flight) clamped to the default tier, fit-all frames the
  connected web, drag-end re-burst, edge hover → tooltip position, HTML overlay for the
  focus node's NAME (Cytoscape has one label per node; the disk shows the initial).
- `codex/Stemma/Stemma.tsx`: rail (wordmark, title, Find a name with inline §6.7 no-match,
  Show ×3 with accent checkboxes, Principal | Everyone + caption, footer "Read to Chapter
  N of M · change" → R3 dialog), canvas top bar ("Focused on X · 1 step" / "The whole web,
  as far as you have read"), controls (Clear focus, +/−, Steps 1/2 only when focused),
  tooltip ("alias · Chapter III" + identity evidence truncated to 80 chars), keyboard
  (`/`, arrows + Enter, Esc), focus resolution (URL `focus` → principal; absent at the new
  chapter → principal quietly; cleared stays cleared), URL mirror via `location.replace`.
- `codex/Stemma/SelectionPanel.tsx`: none / node / edge states per §6.3 with the legend
  rows and "Open X's dossier"; evidence never truncated (§8.4).
- `Input` primitive now `forwardRef` (for `/`). R3's compact chapter list removed from
  the Stemma rail (the §6.3 rail has the footer instead — the R3 shot config and the
  tab-switch fence test now read the footer). MIN LINKS never existed in the new UI; the
  legacy one lives only at `#/_legacy` until R9.
- `tests/fixtures/synthetic-100.json` regenerated (people 60–69 are membership-only
  leaves so folding has something to fold): 101 nodes / 144 edges; R4's dossier numbers
  unchanged (70 people, hub 21 ties).

Spec sections covered: §6.3 all, §7.1–§7.6, §8.3, §8.4 (tooltip/panel), §8.5 (`/`, arrows,
Esc), §9.1 F4 (Stemma variant), §6.7 (no-match inline).

F2 reasoning for the `+N` badge: N counts hidden members that are IN the fenced payload —
entities the reader has already met and that were hidden only by the Principal filter.
Nothing beyond the bookmark exists client-side, so the number cannot encode the future.

Visual comparison (artboard 3, MEASURED — `.shots/phase-5/*`, 15 states × 2 widths,
inspected; fix loops: 3 on the canvas defaults (below), 1 on the controls):
| Element | Status | Note |
|---|---|---|
| Rail: wordmark, title, "Find a name" input (44px, `--deep`) | matches | |
| Show ×3 accent checkboxes | matches | `accent-color: var(--accent)` (P2-permitted) |
| Cast size segmented Principal/Everyone + caption | matches | |
| Footer "Read to Chapter III of 4 · change" | matches | opens the R3 dialog |
| Top bar "Focused on Wren · 1 step" + tabs | matches | |
| Focus disk with initial + name below-right | matches | name is an HTML overlay in Pirata One 28px (≥28 hard rule; spec says 24) |
| 1-hop full ink, rest `--faint` (colour, not opacity); identity `.far` at 0.45 opacity | matches | |
| Identity edge 2.6px `--accent` + glow; structural dashed; social `--dim` | matches | |
| Controls bottom-left: Clear focus, +, − (44×44), Steps | matches | Steps only while focused |
| Right panel edge state: kicker (red for identity), Display 38 title, quote, hairline, legend, outline button | matches | |
| Node state: name, type + first chapter, ties, identity sentence, button | matches spec | (artboard shows the edge state) |
| Nothing selected: legend + hint | matches spec | |
| No-match inline under the field | matches spec | exact §6.7 copy |
| Mural in the canvas centre | matches | none visible; mask holds |
| Red only on identity edges + identity kicker + checkboxes | matches | |
| Far tier (<0.5): labels off except focus + identity endpoints, nodes −20% | matches spec | |
| Close tier (>1.5): all labels full ink | matches spec | |
| synthetic-100 Principal at the default fit | ASSERTED-acceptable | not a hairball: 72 nodes, 17–22 labels, zero overlaps (MEASURED), badges visible. Labels render ≈9px at the 1280×720 minimum (zoom ≈0.53) — small but readable with the halo; the close tier is one wheel-notch away |
| synthetic-100 Everyone | ASSERTED-acceptable | 98 nodes; fit lands ≈0.5–0.63; same label rules |

Fence + E2E (runner summary lines, verbatim):
- `npm run test:fence` → `27 passed (30.6s)` / `4 skipped`
- `npm run test:dossier` → `6 passed (9.4s)`
- `npm run test:stemma` → `10 passed (35.0s)` — walk 1→2→3→4→2 (cy ids == re-derived
  view model of each fixture, Everyone; Principal ⊆; e13 absent before 3; no Veris/
  Sparrow text before 3; no request above per step), F4 Stemma no-match at 2 → resolves
  at 3, shared URL `?focus=12` at bookmark 1 → principal + no leak (hash rewritten,
  no label, panel = Wren, title unchanged), vanishing focus on `[` → principal quietly,
  tooltip (identity with quote / social without) + panel (full quote) + Esc, keyboard
  (`/`, ring, Enter, Esc), lifecycle ×3 (instances == 1, layouts ≤ 1 then 0, 0/0 after
  leaving the work), folding badge == independent count, legibility at 1280×720 (zero
  overlaps, fit in the default tier, synthetic + demo; boxes attached), settle ≤ 1px
  between t=1.2s and 1.5s after a filter change (attached).
- `npm run test:unit` → `Tests  39 passed (39)`
- `npm run test:style` → `5 passed (3.6s)`; `npm run test:geometry` → `13 passed (6.9s)`
- `npm run lint:design` → `lint:design OK — 66 files checked. Legacy allow-list: 3 file(s). Red-permitted: 5 file(s).`
- `npm run typecheck` → (no output, exit 0); `npm run build` → `✓ built in 5.36s`
- `npm run shoot` phases 0–5 → `shoot: OK — 4 / 6 / 12 / 20 / 16 / 30 shots captured, zero console errors.`
- backend `pytest` → `124 passed, 6 skipped in 13.45s`
The dossier shared-URL case was already covered at R4 (fence.spec "F4 (dossier, R4)").

Deleted old code: R3's `<ChapterListCompact/>` removed from the Stemma rail (component
itself stays — the Dossier rail uses it). `Input.tsx` rewritten as forwardRef.

Backend deps hit: none new. D4 alias search = label search over fenced nodes (R0 verdict).

Deviations kept (with reason) — each MEASURED before the change:
- **Cola runs as a finite burst (950ms), not `infinite: true`.** Infinite mode drifted
  105px between t=1.2s and 1.5s after a filter change on synthetic-100. Burst after every
  data/filter change and on drag-end; drag still pins the node; settle is guaranteed.
- **Camera fits on `layoutstop`, never on a timer.** A 700ms-timer fit caught cola
  mid-expansion and left the whole synthetic graph as a far-tier speck.
- **New nodes seeded on a ring, not at the centre.** Centre-piling made cola stack 100
  nodes into a 550×3900 vertical strip inside the burst.
- **Spacing by cast size** (>40 nodes: edgeLength 100/80, nodeSpacing 28, label-inclusive
  overlap avoidance OFF; else the reference 140/110/40 with labels included). With
  label-inclusive boxes the large cast laid out portrait and couldn't fit the default
  tier; with 40/140 the demo overlapped Caelum × Sparrow.
- **Label rules:** above 40 visible nodes only a 22-label budget (identity endpoints
  first, then degree) is drawn at the default tier (§7.5 says "principal labels", not all);
  then a deterministic declutter defers any lower-ranked label whose box collides with a
  kept one — re-run after each settle, after focus changes (the un-focused node's label
  changes from initial to name) and after the 420ms size transition (which moved a label
  8px into its neighbour: the last collision found). Deferred/minor labels return in the
  focus set and at the close tier. This is what makes "zero overlaps" true by construction.
- **Fit-all frames connected nodes only** (isolates drift under cola and dragged the
  fit to the far tier); they stay drawn and reachable.
- Fit-all padding 30 (not 60) above 40 nodes so the default fit stays in the default
  tier at 1280×720. Fits are clamped to zoom ≤ 1.2 so a 3-node focus set isn't drawn at 70px.
- Focus-node name overlay at 28px (Pirata One's floor) instead of §7.1's 24px.
- Org `+N` badge is part of the label text ("the Coil +4") — Cytoscape has no native badge.

BROKEN / open: none.

Open questions for R6:
- **Wren→Caelum is reclassified by the backend at n=4.** The n≤3 payloads carry `e12`
  `SECRET_IDENTITY` (revealed 2); the n=4 payload drops `e12` and carries `e14`
  `TRANSMIGRATED_INTO` (revealed 4) between the same two nodes — the edge id changes. The
  R6 diff (`graph/diff`, keyed on edge id) will therefore see `e14` as a NEW identity edge
  at chapter 4 and play a reveal for a pair the reader already saw revealed at chapter 2,
  while `e12` silently vanishes from the dossier. Recorded only; not resolved here (backend
  frozen; whether R6 should treat "same pair, new relation" as a re-reveal is a design call).

MEASURED (regression guards): see the verbatim lines above.

Commit: (see SESSION_LOG.md Session 6) pushed: yes.

Next: **R6 — Reveal** (§6.5 + §8.2: diff-driven trigger from the R3 forward flow — the
TODO(R6) hook in `ChapterChrome` — choreography with the timings table, pager ≤3, summary
sheet for big jumps, quiet-mode preference, replay buttons in the Dossier identity
blocks, 3s `.just-revealed` highlight on the Stemma/ego graph, aria-live; Playwright
shots at t = 0/450/1000/1400ms + reduced motion). Resolve the open question above first.
Model: Sonnet 5 is fine for the choreography; the open question is a design decision
for you, not a model choice.
