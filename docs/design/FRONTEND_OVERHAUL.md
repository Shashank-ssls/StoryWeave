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
_(Phase 0 fills this: frontend map, payload field names, D1/D4 verdicts, start commands.)_

### Backend deps hit
_(Any spec feature running on its fallback, and why.)_

### Phase reports
_(Paste each phase report here.)_
