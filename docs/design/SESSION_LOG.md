# StoryWeave — Claude Code session log

> Chronological, append-only. One entry per Claude Code session, newest at the bottom.
> A cold-start session reads the latest entry here right after FRONTEND_OVERHAUL.md §9.
> Every session appends its entry before its final commit — including sessions that stop
> mid-phase (FRONTEND_OVERHAUL.md §2 rule 14 / CLAUDE.md rule R6).
>
> Entry shape: date · model + effort · phase(s) touched · start → end commit · what was
> done · decisions and why · issues found (MEASURED / ASSERTED / BROKEN) · where it stopped
> · next step.

---

## Session 1 — R0 Recon + harness (backfilled from FRONTEND_OVERHAUL.md §9)

- **Date:** 2026-09 (exact date not recorded; backfilled)
- **Model / effort:** Sonnet 5 high, per user
- **Phase(s):** R0
- **Commits:** d995a70 (main, environment setup + design package) → e8ff38b (`redesign/codex`)
- **Done:**
  - Frontend recon: no router, `App.tsx` owns all state, `GraphView.tsx` is the only Cytoscape site, `api.ts` → `/api/v1/works/{slug}/graph?n=`.
  - Live Hollow Crown fixtures captured at n=1..4 → `frontend/tests/fixtures/hollow-crown/`.
  - D1 verdict: `evidence_span` present and populated on identity edges. D4 verdict: no alias field, but every alias is its own node, so label search is equivalent.
  - Playwright installed locally, driven via system Chrome (`channel: "chrome"`); `scripts/shoot.mjs` harness + `tests/fence.spec.ts` skeleton (9× `test.fixme`).
  - Baseline "before" shots of the old UI in `.shots/phase-0/`.
- **Decisions:** system Chrome instead of bundled Chromium (download blocked on this network, reversible). Did not pre-create `frontend/src/styles/tokens.css` etc. (would be scaffolding R1/R5 early). Committed pending setup files to `main` first, then branched.
- **Issues:** none BROKEN. MEASURED: pytest 124/6, build clean, shoot 4/4, fence 9/9 fixme.
- **Stopped at:** R0 green, pushed.
- **Next:** R1 tokens & typography.

## Session 2 — R1 Tokens & typography (backfilled from §9)

- **Date:** 2026-09 (backfilled)
- **Model / effort:** Sonnet 5 high, per user
- **Phase(s):** R1
- **Commits:** e8ff38b → d98477a
- **Done:**
  - Fontsource Pirata One / EB Garamond / Alegreya Sans installed; Spectral / IBM Plex removed.
  - `tokens.css` wired globally; old `:root` palette/font block removed from `styles.css`.
  - Primitives: Button, Tabs, Input, Ornament, 9 icons. Hidden `#/_type` gallery.
  - `npm run lint:design` (§4.3 static checks) and `npm run test:style` (§4.2 computed-style checks) added.
- **Decisions:** `#/_type` wired behind a minimal hash check (no router yet — R2's job). Old screens allowed to degrade; documented as "expected-degraded" shots rather than patched.
- **Issues:** `.swatch` class collided with legacy `styles.css` (caught by the radius assertion) → renamed with `tok-` prefix. MEASURED: style 5/5, lint 23 files clean, pytest unchanged.
- **Stopped at:** R1 green, pushed.
- **Next:** R2 shell.

## Session 3 — R2 Shell (backfilled from §9)

- **Date:** 2026-09 (backfilled)
- **Model / effort:** Sonnet 5 high, per user
- **Phase(s):** R2
- **Commits:** d98477a → e764de4
- **Done:**
  - Hand-rolled hash router covering all six routes; `#/_legacy` mounts the old app with `styles.css` loaded lazily.
  - Mural + vignette mounted; four screen shells with measured geometry; Stemma canvas mask.
  - Theme strings object (`codex/theme.ts`) with all §12 keys; `useWorkTitle` reads live `/works`.
  - `npm run test:geometry` (13 assertions) added; lint:design gained a legacy-CSS collision check.
- **Decisions:** legacy files shrink only at R9 (corrected R1's piecemeal guess). Phase 0/1 shot configs left failing-by-design with an inline note (later reversed — see Session 4, Step 1).
- **Issues:** collision-check regex matched `.md`/`.css` in comments → strip comments first. MEASURED: geometry 13/13, style 5/5, lint 39 files, pytest 124/6, fence 9/9 fixme.
- **Stopped at:** R2 green, pushed.
- **Next:** R3 chapter model + fence.

## Session 4 — R3 Chapter model + fence

- **Date:** 2026-09-21
- **Model / effort:** Opus 5, low effort
- **Phase(s):** R3 (+ Step 0 session log, Step 1 harness hygiene)
- **Commits:** e764de4 → (this commit; see `git log`)
- **Done:**
  - Created this log (backfilled R0–R2), rule R6 in CLAUDE.md, §2 rule 14 + §8 in FRONTEND_OVERHAUL.md.
  - Phase 0/1 shot configs retargeted at `#/_legacy` / `#/_type`; phases 0/1/2/3 all pass.
  - `codex/chapter/`: bookmark store (validated localStorage), `ChapterProvider` (single in-flight fetch, AbortController + request token, cache ≤ bookmark with sync purge on back, forward/backward flows, §6.7 error rule), `ChapterListCompact`, `ChapterDialog`, `ChapterChrome` (wash, banner, toasts, `[`/`]`), `roman`; `graph/diff` pure + unit tested. Provider keyed by slug in `CodexApp` so all three tabs share one model.
  - Fence suite: 25 passing / 5 fixme (each fixme names its phase); Vitest 2.x added (`npm run test:unit`, 11/11).
  - Shots of dialog (default/invalid/loading), rail at ch 1/2/4, Stemma rail, banner, both toasts at both widths; compared to artboards 2 and 6 (rendered via Chrome — no pdftoppm on this machine).
- **Decisions:** Vitest pinned to 2.x (5.x needs Vite 6). Backward-fetch failure shows no data rather than the old higher-chapter data (safer than §6.7's literal wording). Keys use a guarded window listener (focus on `<body>` never reaches a root-element handler). Per-shot `expectedConsoleErrors` in shoot.mjs for the injected-500 shot.
- **Issues:** MEASURED — `recordGraphRequests` matched Vite's `src/graph/diff.ts` URL (helper bug, fixed); my first "slow older response" test was a no-op (`[` at chapter 1) and rewritten; `]` opened an inert dialog for an unknown slug (fixed: gated on chapter_count). Nothing BROKEN. All suites green: pytest 124/6, typecheck, build, lint:design 52 files, style 5/5, geometry 13/13, fence 25/25 (+5 fixme), unit 11/11, shoot 0/1/2/3 zero console errors.
- **Stopped at:** R3 green, committed and pushed.
- **Next:** R4 Dossier (Sonnet 5 recommended).

## Session 5 — R4 Dossier (same session as R3, continued)

- **Date:** 2026-09-21
- **Model / effort:** Opus 5, low effort (user asked for Sonnet 5; the model can't be switched mid-session, user said "go" on Opus)
- **Phase(s):** R4 (+ Step 0 R3 follow-up, Step 1 graph foundation pulled forward from R5)
- **Commits:** 46809ea → (this commit; see `git log`)
- **Done:**
  - `graph/viewModel.ts` (pure, 25 unit tests) + `graph/codexStyle.ts` port; GraphView.tsx → legacy allow-list.
  - `ChapterProvider.prevData` (n−1 through the same cache, own controller) for F8.
  - Dossier complete: `CastList`, `EntityMain`, `EgoGraph` (concentric), `StateCard` (§6.7), skeleton, not-present, error card, principal redirect, fence line.
  - `tests/dossier.spec.ts` (6 E2E incl. the 1→2→3→4→2 DOM-vs-fixture walk), F4 dossier + F8 activated in fence.spec (27 pass / 4 fixme), `synthetic-100.json` + generator.
  - Phase-4 shots (16) inspected vs artboard 2; comparison table in §9.
- **Decisions:** error card replaces the banner whenever nothing is on screen; identity sentence keeps source→target order; changed tags empty at ch 1; ego 2-hop ring capped at 40 nodes; fence tooltip = native `title`.
- **Issues:** MEASURED — rail cast clipped instead of scrolling (fixed); "one bonds recorded" (fixed with `ledeOne`); synthetic hub ego graph zoomed labels away (capped); my first Step 0 test scenario had chapter 1 already cached by the new n−1 fetch (rewritten to start at 4); three R3 fence expectations updated for the legitimate n−1 request. Backend note: n=4 replaces e12 SECRET_IDENTITY with e14 TRANSMIGRATED_INTO (frozen, documented). Nothing BROKEN.
- **Stopped at:** R4 green, committed and pushed.
- **Next:** R5 The Stemma (Sonnet 5 recommended).

## Session 6 — R5 The Stemma (same session, continued)

- **Date:** 2026-09-21
- **Model / effort:** Opus 5, low effort
- **Phase(s):** R5
- **Commits:** 5617de5 → (this commit; see `git log`)
- **Done:**
  - `graph/stemmaModel.ts` (principal filter + folding, focus set, tiers, label budget + declutter, fenced search; 39 unit tests total), `codexStyle` extended, `cyRegistry` (dev-only lifecycle counters + Stemma handle).
  - `StemmaCanvas` (cola burst lifecycle, diff-apply, focus/preview/selection/kbd classes, tiers, fit-on-layoutstop, tooltip, focus-name overlay), `Stemma` screen (rail, controls, keyboard, focus/URL resolution), `SelectionPanel`.
  - `tests/stemma.spec.ts` 10/10 (walk, F4, shared-URL leak, vanishing focus, tooltip/panel, keyboard, lifecycle, folding, legibility @1280, settle). Phase-5 shots (30) inspected vs artboard 3.
  - Synthetic fixture regenerated with membership-only leaves; R3 shot + one fence test updated for the §6.3 rail footer.
- **Decisions:** finite cola burst (950ms) instead of infinite; fit on layoutstop; ring seeding; spacing by cast size; 22-label budget + deterministic declutter; fit-all excludes isolates; fit zoom clamp 1.2; name overlay 28px; badge in label text. Each backed by a measurement recorded in §9.
- **Issues:** MEASURED — infinite cola drift 105px; timer-fit → far-tier speck; centre seeding → 550×3900 strip; 40 label overlaps → 10 → 5 → 1 (size transition) → 0; clearing focus was undone by the URL-resolution effect (fixed with undefined/null states); Vite dev server died once mid-run (restarted, logged to `.local/vite-dev.log`). Nothing BROKEN.
- **Stopped at:** R5 green, committed and pushed.
- **Next:** R6 Reveal — resolve the §9 "Open questions for R6" (Wren→Caelum reclassified at n=4) first.

## Session 7 — R6 Reveal moment

- **Date:** 2026-09-22
- **Model / effort:** Sonnet 5, high effort
- **Phase(s):** R6
- **Commits:** 0192720 → (this commit; see `git log`)
- **Done:**
  - Recorded your RESOLVED decision for the §9 open question (pair-keyed identity diff;
    normal / deepening / no-reveal rules) in FRONTEND_OVERHAUL.md §9 before building.
  - `graph/diff.ts` rewritten: pair-keyed `classifyReveal`/`diffGraphs` returning
    `reveals: Reveal[]`; also closed a real gap (P5/§8.4 "no quote, no edge" wasn't applied
    to reveals) found while building it. `newIdentityEdges` removed; `ChapterChrome`/
    `useDossier` updated to read `reveals` instead (same F8 behaviour).
  - `codex/reveal/`: `RevealContext`, `RevealChrome` (orchestrator: overlay vs. summary
    sheet vs. quiet toast, shared 3s highlight timer, quiet-mode preference), `RevealOverlay`
    (§6.5 layout, §8.2 choreography via CSS keyframes, pager, focus trap, Esc/click-outside,
    aria-live), `RevealSummarySheet`, `revealPrefs.ts`.
  - `ChapterProvider`: `pendingReveal`/`dismissReveal` (forward-commit-only) + read-only
    `getCachedPayload` for the Dossier's cache-only replay.
  - Dossier: replay icon button per identity block (new `ReplayIcon`) + 3s `.justRevealed`
    highlight. Stemma: `.just-revealed` glow pulse via `cy.animate()`, deferred to after the
    canvas's first settle.
  - `Button` made `forwardRef` (overlay moves focus to it programmatically).
  - New suites: `tests/reveal.spec.ts` (11/11), `tests/reveal-choreography.spec.ts` (3/3,
    real-elapsed-time sampling — CSS animations aren't affected by `page.clock`). 7
    pre-existing fence tests fixed (every forward step in the demo now reveals something,
    so their next click was blocked by the overlay's backdrop) via a `stripReveals` route
    helper; `dossier.spec.ts`/`stemma.spec.ts`'s walk tests got `dismissRevealIfShown`
    instead (they want the real reveals). Phase-6 shots (14, both widths) vs artboard 5.
- **Decisions:** backdrop renders its own mural+vignette (opaque) instead of dimming the
  live screen through `--scrim` — a real legibility bug (identity-block text bled through
  behind the headline), fixed same-session, documented in FRONTEND_OVERHAUL §9. Jump-far
  (>3 reveals) always shows the summary sheet even in quiet mode. New `ReplayIcon` added to
  the icon set (not in the original §4.4/§14 table, which predates R6).
- **Issues:** MEASURED — the backdrop bleed-through (found via the first `reveal-deepening`
  shot, fixed); a real focus-trap/Esc bug found via reasoning before it ever shipped (the
  content div's `onKeyDown` only sees events bubbling from a focused DESCENDANT, but focus
  doesn't land inside the overlay until the 1250ms choreography delay — Esc would have been
  a no-op for up to 1.25s; moved to a window-level listener, same pattern as `[`/`]`).
  **BROKEN, not fixed (pre-existing, out of R6 scope):** the Stemma's camera fit lands
  off-screen after ANY in-app SPA navigation into the tab (reproduces with a plain Dossier→
  Stemma tab click, no reveal involved) — found via the `stemma-just-revealed` shot; one fix
  attempt (defer the highlight pulse until after first settle) did not resolve it, confirming
  it isn't caused by this phase. Logged in FRONTEND_OVERHAUL §9 for a decision. One
  `test:stemma` run showed a flaky failure (pre-existing legibility test) under heavy
  concurrent-process load from this session; re-ran in isolation, passed clean.
- **Stopped at:** R6 green, committed and pushed.
- **Next:** R7 Chronicle (Sonnet 5 recommended).

## Session 8 — R7 Chronicle

- **Date:** 2026-09-22
- **Model / effort:** Sonnet 5, high effort
- **Phase(s):** R7, R8 (of R7→R8→R9 planned for this session; stopped before R9 on
  explicit user instruction mid-session — see below)
- **Commits:** 782998b → b475ded (R7) → 056fac7 (R8)
- **Done:**
  - `graph/chronicleModel.ts` (new, pure, 13 unit tests): `chronicleRows` (reuses
    `stemmaModel.visibleGraph`'s principal/everyone filter), `columnLayout` (small ≤12 /
    large >12 chapters-to-bookmark, blocks-of-50 header bands, F3 by construction),
    `stitches`, `identityTimeline` (replays R6's own `diffGraphs` across cached chapters —
    no new classification logic).
  - `ChapterProvider.ensureHistory(upTo)` (new): F1-safe best-effort backfill of chapters
    1..bookmark into the shared cache, so the identity timeline has full history.
  - `codex/Chronicle/Chronicle.tsx` rebuilt from the R2 placeholder: name column + one
    horizontally-scrollable SVG (chapter/band headers, presence threads, curved stitches,
    identity links with ringed dots + labels, bookmark line, constant-width sealed band),
    right panel (kicker/title/quote/explanation/pager/"Read on"). 15 new theme strings.
  - New suite `tests/chronicle.spec.ts` (8/8): fenced walk with an independent
    identity-timeline re-derivation, F3 in both layout modes, "Read on" dialog-only path,
    no page-level horizontal scroll with a large synthetic cast/book. Phase-7 shots (14,
    both widths) vs artboard 4.
- **Decisions:** proportional column width (28px) and block size (50) are this build's own
  pragmatic choice (spec gives small-mode figures only); Chronicle's explanation line uses
  one template for every identity relation (the spec's own single given example); both
  names in the panel title are clickable links (no "current entity" to exclude, unlike
  Dossier).
- **Issues:** MEASURED, both found via screenshot comparison and fixed same-session — (1)
  React StrictMode's dev-mode double-invoke cancelled the scroll-to-bookmark effect's first
  `requestAnimationFrame` and then the second invocation's "already done" guard skipped it
  entirely, so the chart silently never scrolled; fixed by only marking the ref done inside
  the frame callback. (2) `ChapterProvider` sets the bookmark before it commits `data`, so
  the scroll effect's dependencies had already taken their final value before the chart's
  own DOM existed and never changed again once it mounted; fixed by adding `vm` as a real
  dependency. Root-caused both with a throwaway Playwright script reading
  `scrollLeft`/`getBoundingClientRect` directly rather than guessing from screenshots.
  Nothing left BROKEN.

**R7 done, pushed (b475ded). Continued straight into R8 per the session plan.**

- **R8 done:**
  - `codex/Landing/TryItPanel.tsx`: the try-it panel is its own `<ChapterProvider
    slug={DEMO_SLUG}>` + real `<RevealChrome>`/`<ChapterChrome/>` — a second MOUNT of the
    exact machinery the rest of the app uses, not a reimplementation, so it shares the same
    `storyweave:bookmark:the-hollow-crown` key and plays the real R6 overlay on a reveal.
  - `codex/Landing/ChapterStepper.tsx` (per-chapter buttons ≤8 chapters, compact
    prev/current/next above that), `MiniGraph.tsx` (non-interactive codexStyle Cytoscape
    from the same ViewModel — F9 holds by construction), `ExplainerPanel.tsx` ("How the
    seal works": 3 sentences + inline SVG diagram).
  - `Landing.tsx` rebuilt: header, left column (real lede/trust line), try-it slot
    (loading/error/demo-missing/live off a plain `/works` fetch), footer shelf (real
    works + "Add a novel" → the existing `#/_legacy` Composer, no new ingestion UI built
    per the brief). All §6.7 state cards wired.
  - New suite `tests/landing.spec.ts` (9/9): F9, F2, stepper forward/backward through the
    real commit path, "Explore the full book", all three /works-driven states, the
    explainer, and a CLS (`PerformanceObserver` layout-shift) check ≤2%. Un-fixme'd F4
    (search) and F9 in `fence.spec.ts` with real tests (29/31, 2 fixme: F6/F7, still
    config-absent). Phase-8 shots (14, both widths) vs artboards 1 and 7.
- **R8 decisions:** the eye-glyph prompt copy is generic ("Step forward. Someone is not
  who they seem."), not spec's literal chapter-naming example — read literally as a
  computed runtime string, that example would itself be the F9 hint it forbids; kept it
  theme-string-generic instead. Demo-missing and empty-shelf render together when
  `/works` returns 0 (no API signal to tell them apart, per the brief's own escape hatch).
- **R8 issues:** MEASURED, a real font-swap CLS bug found via the new test, not guessed —
  the H1's serif fallback rendered ~88px taller than Pirata One, and the stepper's 4
  buttons wrapped onto two rows under the fallback UI font before collapsing to one; ~6%
  CLS combined, 3x budget. `font-size-adjust: from-font` didn't help; a `min-height`
  reservation fixed the number but left a permanent visible gap. Fixed with `max-height:
  264px; overflow: hidden` on the H1 (local fonts resolve in single-digit ms, so nothing
  is perceptibly clipped) and `flex-wrap: nowrap` + shrinkable buttons on the stepper
  (removes the wrap state a font-metric change could ever move something between rows
  of). Root-caused with a throwaway script sampling `PerformanceObserver` layout-shift
  sources' `previousRect`/`currentRect`. Two PRE-EXISTING tests had stale hardcoded
  expectations once landing had its own live graph/provider (a network-request-count
  assertion in `fence.spec.ts`, a cytoscape-instance-count assertion in
  `stemma.spec.ts`) — both updated with the reasoning inline, not silently patched.
  Nothing left BROKEN.
- **Stopped at:** R8 green, committed and pushed — **on the user's explicit instruction
  mid-session to stop before R9**, not a context or failure boundary. R9 has not been
  started: no files touched, no plan drafted beyond what FRONTEND_OVERHAUL §9's existing
  "Next" note already said.
- **Next:** R9 Polish & acceptance (fix the logged Stemma camera-fit bug first, then label
  legibility, keyboard map, screen-reader mirror, responsive breakpoints, reduced-motion
  audit, favicon/OG, delete `#/_legacy` + all legacy code, run the §16 checklist). A fresh
  session should read this entry, confirm clean on `redesign/codex`, and start R9 from
  scratch — nothing here is mid-phase.

## Session 9 — R9 Polish & acceptance, steps 1-4 (mid-phase stop)

- **Date:** 2026-09-22
- **Model / effort:** Sonnet 5, high effort
- **Phase(s):** R9 (steps 1-4 of the 10-step R9 scope; steps 5-10 not started)
- **Commits:** 9772dd3 → 8255430 (steps 1-2) → 562832c (steps 3-4)
- **Done:**
  - **Step 1 — Stemma camera-fit bug (logged at R6/R7, `FRONTEND_OVERHAUL.md` §9).**
    Root-caused via a throwaway `window.__dbg` event log (mount/dataEffect/runPhysics/
    layoutstop/fitFocusNow, each timestamped) rather than guessed: cytoscape-cola fires
    `'layoutstop'` TWICE per burst on graphs small enough to hit its own
    `convergenceThreshold` early (measured: 11ms into a 950ms `maxSimulationTime` burst) —
    once on that premature "convergence" stop (near-seed positions), again at the real
    duration. `StemmaCanvas.tsx`'s `refitOnStop`/`settledRef` treated the first stop as
    final, so the real settle's refit never ran. Fixed with an elapsed-time gate
    (`layoutStartedAt`/`layoutSettleMs`, ignore any stop before the burst's own declared
    duration) plus a `suppressNextStop` guard for the separate case of `runPhysics()`
    manually `.stop()`-ing a still-running layout to supersede it (also fires
    `'layoutstop'`, also was consuming the same flag). Three regression tests added to
    `stemma.spec.ts` (Dossier→Stemma, Chronicle→Stemma, landing→Explore→Stemma tab
    clicks) — MEASURED to fail against the pre-fix code (reverted via `git stash`, re-ran,
    confirmed failing, restored), so they're proven non-vacuous.
  - **Step 2 — label legibility (§16).** New `stemma.spec.ts` test measuring
    font-size×zoom on the default (focused-on-principal) view at 1280×720: demo passed
    immediately (20.4px); synthetic-100 measured 8.7-8.9px (below the 13px floor) because
    a hub principal's focus fit was framing all 22 of its near-nodes. Tried ranking by
    graph importance (identity/degree, same as the label budget) first — measured almost
    no zoom change, because a high-degree neighbour's OTHER ties pull cola to place it far
    from the focus regardless of rank. Fixed instead with `FIT_FOCUS_BUDGET` (12): the
    camera fits the focus node plus its 12 spatially NEAREST ties in the settled layout;
    every tie still draws, labels and positions normally regardless of budget (only the
    CAMERA framing is capped). MEASURED after: demo 20.4px, synthetic-100 19.4px.
  - **Step 3 (§8.5).** `codex/shortcuts/useGlobalShortcuts.ts` + `ShortcutSheet.tsx`: `g d`/
    `g w`/`g c` chords (900ms window) and `?`'s shortcut sheet (real focus trap, same
    scrim/dialog pattern as the Change-chapter dialog). Guarded by the existing
    typing-target pattern plus a new `[role="dialog"][aria-modal="true"]` check so it never
    fights the chapter dialog or reveal overlay. `tests/shortcuts.spec.ts` (5/5).
  - **Step 4 (§11).** Off-screen `aria-live="polite"` mirror of the focused neighbourhood
    in `Stemma.tsx` ("Wren — ties: Prince Caelum (transmigration, Chapter IV), …"), built
    only from the same fenced view model the canvas draws from. New `stemma.spec.ts` test
    confirms it updates on focus change and never leaks a later-chapter tie at an earlier
    bookmark.
- **Decisions:** WIP-committed after steps 1-2 and again after 3-4 (session rules: commit
  after 1-2 and 8, final commit after 10) rather than pushing at each — pushed once, now,
  at the mid-phase stop. Distance-based (not importance-based) ranking for the fit budget
  — measured, not assumed, to be the one that actually moves the zoom.
- **Issues:** MEASURED, both root-caused with instrumentation, not guessed — the double
  `'layoutstop'` fire (step 1) and the importance-ranking-doesn't-shrink-the-frame result
  (step 2, kept as a documented dead end in the code comment so a future session doesn't
  retry it). Nothing left BROKEN in steps 1-4.
- **Stopped at:** step 4 of 10 green, committed (562832c) and pushed. Steps 5-10 (responsive
  breakpoints, reduced-motion audit + full shoot, favicon/OG, `#/_legacy` + legacy-code
  deletion with grep proof, the §16 acceptance checklist line by line, and the final full
  suite + full 1440×900/1280×720 shoot) are **not started** — stopped here on token-budget
  grounds (explicit session rule), not a failure. All suites confirmed green at this commit:
  backend `pytest` 124/6 (unchanged all session), `typecheck` clean, `lint:design` 83 files
  clean, `test:unit` 63/63, `test:stemma` 15/15, `test:shortcuts` 5/5, `test:reveal` 11/11,
  `test:dossier` 6/6, `test:chronicle` 8/8, `test:landing` 9/9, `test:fence` 29/29 (+2
  fixme, F6/F7 still config-absent), `test:style` 5/5, `test:geometry` 13/13.
- **Next:** R9 steps 5-10, in the order FRONTEND_OVERHAUL.md §9's task brief gives them.
  Step 5 (responsive) and step 6 (reduced motion) are the two most likely to need real
  visual judgment calls (drawer/bottom-sheet behaviour, physics-finite verification) — a
  fresh session should re-read this entry, confirm clean on `redesign/codex` at 562832c,
  restart the dev stack, and continue straight into step 5 without re-deriving steps 1-4.

## Session 10 — R9 continued: user-reported bugs + step 5 (responsive), stopped on request

- **Date:** 2026-09-22
- **Model / effort:** Sonnet 5, high effort
- **Phase(s):** R9 (step 5 of 10 completed this session; steps 6-10 not started — user
  asked mid-session to stop after step 5, "we will resume others later")
- **Commits:** 0fd0309 → 3f5da2f (bug fixes) → 6ea8d35 (step 5)
- **Started from:** a fresh session, dev servers not running (stopped at the end of Session
  9); the user's first message included a screenshot showing the landing page's try-it
  panel erroring ("The archive didn't answer") because of exactly that — restarting
  `dev.ps1` + uvicorn + vite resolved it immediately, not a code bug.
- **Done (bug fixes, before step 5):**
  - **Scrollbars hidden, still functional.** Global rule in `tokens.css`
    (`scrollbar-width: none` / `-ms-overflow-style: none` / `::-webkit-scrollbar{display:
    none}` on `*`). Verified the Chronicle's horizontal chart still scrolls via
    `scrollLeft` with no visible thumb.
  - **Stemma small-cast node clipping ("node fluidity").** A focus fit only ever framed
    the near+focus set; a dimmed "far" context node (not in that set, still drawn) could
    land partly off the canvas edge — measured live: Lady Veris rendered half off the top
    edge on the demo's 6-node graph at bookmark 4. Below `FIT_ALL_WHEN_SMALL` (20 total
    nodes) there's no legibility pressure at all (the R9 `FIT_FOCUS_BUDGET` only matters
    for a 13+-tie hub), so `fitFocusNow` now fits the whole connected web in that case.
    New Playwright test asserts every node's rendered centre stays on-canvas; the three
    existing camera-fit tests' centering tolerance widened to 5%-95% since fitting the
    whole small web no longer centres the focus node when other nodes pull the frame wider
    on one side.
  - **Font audit ("some are not integrating properly"): no bug found.** Checked computed
    `font-family` on every leaf DOM node app-wide (all three token fonts, zero fallback),
    `document.fonts` network requests (all six weight/style files 200, none 404), the
    Cytoscape canvas stylesheet's literal font mirrors, `lint:design` (0 raw font-family
    literals) and `test:style` (fonts actually loaded, not fallback) — all clean. Screens
    individually inspected (landing, Dossier, Stemma, the `?` shortcut sheet) show the
    intended three-role system (Pirata One display / EB Garamond body / Alegreya Sans UI)
    consistently. Flagging as ASSERTED-clean rather than claiming the user's original
    concern is fully explained — nothing reproduced, so there's nothing further to fix
    without a more specific report.
- **Done (R9 step 5 — responsive, §11):**
  - 1024-1279: Dossier's and Stemma's right panels, and Chronicle's right panel, collapse
    into toggle drawers — closed (off-canvas) by default, a `Button` toggle + scrim opens/
    closes them, Esc also closes. Chronicle's is a bottom sheet (no left rail to spare);
    Dossier/Stemma's are right-side slide-ins, labelled "Show the Stemma" / "Show
    selection" per the spec's own example wording.
  - <1024: Dossier's and Stemma's left rail additionally becomes a top drawer (single
    column, "Cast & chapters" toggle), on top of the panel-drawer behaviour already active.
  - **Real bug found and fixed same-session:** the first-pass CSS declared each screen's
    responsive `@media` block near the TOP of its `.module.css`, before the base `.rail`/
    `.rightPanel`/`.topRow` rules further down. Same specificity → later rule wins in the
    cascade regardless of the media query matching, so the drawer silently never activated
    (measured: `.rightPanel` stayed `position: sticky` at 1100px width even though the
    override rule's `max-width: 1279px` query matched). Fixed by moving all three
    responsive blocks to the end of their stylesheets. Also fixed a related crowding bug
    (toggle button + section label + tabs collided on one line at 1024-1279) by making
    `topRow`/`canvasTopBar`/`headerBar` wrap, with the toggle forced onto its own row.
  - New tests in `tests/geometry.spec.ts`: no horizontal scroll at 1100×800 and 900×800 for
    all three screens (9 tests), plus toggle-mechanics tests (off-canvas by default, opens
    on toggle, closes on scrim) for the Dossier panel drawer, Dossier rail drawer and the
    Chronicle bottom sheet (3 tests) — these specifically would have caught the
    cascade-order bug above.
- **Issues:** MEASURED, both found and fixed same-session (see above) — the CSS
  cascade-order bug (real, would have shipped a fully broken responsive mode) and the
  topRow crowding bug. Nothing left BROKEN.
- **Stopped at:** step 5 of 10 green, committed (6ea8d35) and pushed — **on the user's
  explicit mid-session instruction to stop after step 5**, not a context or failure
  boundary. Steps 6-10 (reduced-motion audit + full shoot, favicon/OG, `#/_legacy` +
  legacy-code deletion with grep proof, the §16 acceptance checklist, and the final full
  suite + full 1440×900/1280×720 shoot) have **not been started**. All suites confirmed
  green at this commit: backend `pytest` 124/6 (unchanged), `typecheck` clean,
  `lint:design` 83 files clean, `test:unit` 63/63, `test:stemma` 16/16, `test:shortcuts`
  5/5, `test:reveal` 11/11, `test:dossier` 6/6, `test:chronicle` 8/8, `test:landing` 9/9,
  `test:fence` 29/29 (+2 fixme), `test:style` 5/5, `test:geometry` 22/22.
- **Next:** R9 step 6 (reduced-motion audit: physics finite, no line drawing, reveal as a
  plain 200ms fade, loading dots static — then a full shoot with reduced motion emulated),
  then steps 7-10 as FRONTEND_OVERHAUL.md §9's task brief lists them. A fresh session
  should re-read this entry, confirm clean on `redesign/codex` at 6ea8d35, restart the dev
  stack, and continue straight into step 6 without re-deriving steps 1-5.

## Session 11 — R9 step 6 (reduced-motion audit)

- **Date:** 2026-09-22
- **Model / effort:** Sonnet 5, high effort
- **Phase(s):** R9 (step 6 of 10)
- **Commits:** 07c5260 → (this commit; see `git log`)
- **Started from:** a fresh session, dev servers not running; restarted `dev.ps1` +
  uvicorn (`storyweave-demo.sqlite`) + `npm run dev` before touching anything.
- **Done:**
  - **Audited the four reduced-motion requirements (§4.5/§6.7) one by one, against the
    real running app, not by re-reading old code:**
    1. Physics finite — already correct (`GraphView`/`StemmaCanvas`/`colaOptions` all
       branch on `matchMedia("(prefers-reduced-motion: reduce)")`, `maxSimulationTime`
       800ms). Previously unverified by any suite; now MEASURED by a new test (below).
    2. No line drawing — already correct: `RevealOverlay.module.css`'s `.reduced .thread`
       drops `threadDraw` entirely and only fades (built at R6). Already covered by
       `reveal-choreography.spec.ts`'s existing reduced-motion test; nothing to fix.
    3. Reveal as a plain 200ms fade — already correct, same R6 code, same existing test.
    4. **Loading dots static — real gap found: the dots didn't exist at all.** The §6.7
       Loading state card's spec'd "3-dot line glyph (ink→dim→faint; fade in sequence,
       1.2s loop; static under reduced motion)" was never built — all three of its
       `StateCard` call sites (Chronicle's chart skeleton, the landing try-it panel's
       loading state, and the `/works`-list loading state) passed `body=""` and no glyph,
       silently dropping both the required body sentence and the dots. Found by reading
       every `stateLoading` call site, not assumed from the spec table.
  - **Fix:** new `codex/states/LoadingDots.tsx` + `.module.css` (3 spans, `dotFade`
    keyframe cycling ink↔faint with staggered 0/150/300ms delays for the "fade in
    sequence" look under full motion; a `prefers-reduced-motion` media query kills the
    animation and fixes the three dots to ink/dim/faint respectively — the spec's own
    literal order, held still). `StateCard` gained an optional `loading` prop that
    appends `<LoadingDots/>` after the body paragraph. Chronicle's skeleton and the
    landing try-it panel's loading state now also fill in the real body sentence
    (`loadingUpTo`, templated with `m.loading ?? m.bookmark`) they'd been dropping; the
    `/works`-list loading state (no chapter context available pre-fetch) gets the dots
    only, body stays empty — the spec's example sentence doesn't apply before any work
    has loaded.
  - **New suite `tests/reduced-motion.spec.ts` (4/4)**, none of it existed before this
    session: global `--dur-*` token collapse under emulated reduced motion; Stemma
    physics genuinely stops (positions stable within 1px, sampled after its own declared
    800ms burst) rather than just animating more calmly; loading glyph static + 3
    distinct held colors under reduced motion; loading glyph staggered/animating under
    full motion. `npm run test:reduced-motion` added to `package.json`.
  - **`scripts/shoot.mjs` gained a `--reducedMotion=reduce` flag** (sets
    `browser.newContext({ reducedMotion })`, real Playwright emulation, output goes to
    `.shots/phase-<n>-reduced-motion/`) and a new phase-9 shot set (`reveal-normal`,
    `stemma-settled`, `loading-dots-chronicle`) reusing R6's own `atChapter`/`confirm`
    helpers. Ran it: 6/6 shots, zero console errors. Inspected all six — reveal overlay
    fully drawn (thread, eye, all text) after 500ms with nothing mid-animation; Stemma
    canvas settled and legible with no drift artifacts; Chronicle's loading card now
    shows the real sentence + three static dots exactly as spec'd.
- **Decisions:** kept the `/works`-loading state's body empty rather than inventing
  chapter-specific copy it has no chapter to describe (no ChapterProvider exists yet at
  that point in Landing.tsx) — dots-only there, full sentence+dots everywhere a chapter
  number is actually known. `LoadingDots` is `aria-hidden` (decorative; the card's own
  `role="status"` + label already announce "Loading").
- **Issues:** MEASURED — the missing loading-dots glyph (real spec gap, not a regression,
  fixed same-session). Nothing left BROKEN. Full regression pass after the fix: backend
  `pytest` 124/6 (unchanged), `typecheck` clean, `build` clean, `lint:design` 85 files
  clean (2 new files), `test:unit` 63/63, every existing Playwright suite re-run and
  unchanged (`test:fence` 29/29 +2 fixme, `test:dossier` 6/6, `test:stemma` 16/16,
  `test:reveal` 11/11, `test:reveal-choreography` 3/3, `test:chronicle` 8/8,
  `test:landing` 9/9, `test:shortcuts` 5/5, `test:style` 5/5, `test:geometry` 22/22),
  plus the new `test:reduced-motion` 4/4.
- **R9 step 7 (favicon/OG, §14) — done, same session:**
  - `public/favicon.svg`: a wax-seal disc (ink on bg, same motif as `RevealOverlay`'s
    `.seal`) with a bold serif "S". Spec's literal wording is "in Pirata One", but a
    favicon is a standalone resource with no access to the page's `@font-face` rules —
    embedding the whole variable font as base64 to label a 16px icon isn't a reasonable
    trade, so it's drawn in a generic serif instead (documented deviation). **Real bug
    found and fixed while building it:** the SVG's own descriptive `<!-- -->` comment
    contained the literal substring `--bg`, and XML comments cannot contain `--`
    anywhere inside them — every browser silently failed to parse the whole file, so the
    icon rendered as a broken-image glyph even though the file 200'd. Caught by actually
    rendering it (a raw `page.goto` to the SVG surfaces the browser's own "error on line
    2" report; an `<img>` tag alone just shows a generic broken icon with no reason),
    not assumed from a green network log. Verified after the fix at 16/32/64/128px, all
    legible.
  - `public/og-image.png` (1200×630, "landing H1 over mural" per spec): generated by
    rendering a throwaway HTML fixture that reuses the real `.mural`/`.vignette` classes
    from `tokens.css` and the real theme strings (`landingH1`, `landingKicker`) — not a
    hand-drawn approximation — through Playwright and screenshotting it, the same
    "measure the real thing" approach as the rest of this project's tooling. The fixture
    HTML and generator script were both deleted after use (throwaway, like the CLS/
    camera-fit debug scripts earlier in R9); only the resulting PNG is committed.
  - `index.html`: `<link rel="icon">`, a meta description, and og:/twitter: tags (title,
    description, image + dimensions, summary_large_image card) using the same copy as
    the landing page.
  - MEASURED: `build` clean, both assets land in `dist/` at their referenced root paths;
    `lint:design` 85 files (unchanged — neither file type is linted); `typecheck` clean;
    `test:geometry` 22/22 and `test:style` 5/5 re-run clean (no regression from the new
    `<head>` content).
- **R9 step 8 (`#/_legacy` + legacy-code deletion, with grep proof) — done, same
  session:**
  - **Real conflict found before deleting anything, and taken to you rather than
    guessed:** the spec-required "Add a novel" link (§6.1) had its only working
    implementation inside the legacy app (R8's own decision: "no new ingestion UI built
    per the brief," reusing the legacy Composer via `#/_legacy`). Deleting the legacy
    route wholesale, as R9's plan said, would have silently killed the one working
    ingestion flow. You chose to port the Composer into the Codex UI as a real route
    rather than lose the feature or leave a partial exception.
  - **Ported:** `codex/Compose/Composer.tsx` (same state machine, same four API calls —
    `ingestWork`/`previewChapters`/`fetchStatus`/`appendChapters`, unchanged per R3's
    backend freeze — restyled with `Button`/`Input`/the new `LoadingDots` in place of the
    old CSS spinner) + `Compose.tsx` (the route screen: header, centered card, on the
    same mural/vignette every other screen sits on) + `Composer.module.css` /
    `Compose.module.css`, both tokens-only. New route `#/add` (`router/useHashRoute.ts`,
    `CodexApp.tsx`). Both "Add a novel" call sites in `Landing.tsx` now go there instead
    of `#/_legacy`; `appendChapters` mode is kept fully working in the component but has
    no new-UI entry point (the old per-work "add chapters" trigger lived in the retired
    Library screen, and nothing in DESIGN_SPEC specs a replacement) — documented in the
    component's own header comment rather than silently dropped.
  - **Also fixed while touching this code:** the empty-shelf state's "Open the sample"
    button pointed at `#/_legacy` too, which — once deleted — would have been a dead
    link even in the old build's own behavior (the legacy library would show nothing
    useful in the zero-works case either). Now navigates straight to the demo Dossier.
  - **Deleted whole** (grep-verified — see below): `src/App.tsx`, `src/GraphView.tsx`,
    `src/Library.tsx`, the old `src/Composer.tsx`, `src/codex/LegacyRoute.tsx`,
    `src/styles.css`.
  - **Trimmed, not deleted** (files with a real, still-needed half and a legacy-only
    half — read every export's call sites before touching anything, not assumed from
    the file's name): `src/ontology.ts` lost `NODE_TYPES`/`NodeTypeName`/`TYPE_COLOR`/
    `typeColor`/`REVEAL`/`GROUND`/`INK`/`INK_DIM`/`EDGE_QUIET`/`relationLabel`/
    `relationStepLabel` (all GraphView-Cytoscape-only; `DEMO_SLUG`/`IDENTITY_RELATIONS`/
    `RELATION_LABELS` stay, used throughout the Codex UI). `src/api.ts` lost
    `fetchGraph`/`deleteWork` (both legacy-only; `ChapterProvider` has always had its own
    fenced fetch with abort support, never called `fetchGraph`). `scripts/lint-design.mjs`
    lost the `LEGACY_FILES` hex/font-family exemption list and the whole rule-4 "collides
    with legacy styles.css" check (and its now-dead `extractClassNames` helper) — both
    existed only for files that no longer exist. `scripts/shots.config.mjs` lost phase
    0's two shots and phase 1/2's three `#/_legacy`-targeting shots (they can never run
    again; a comment points at SESSION_LOG's R0/R1/R2 entries for what they used to
    show). `tests/geometry.spec.ts`'s "`#/_legacy` behaves unchanged" test replaced with
    one covering `#/add` instead (form renders, both "Add a novel" links route there).
  - **Grep proof:** `grep -rln "_legacy"` across `frontend/{src,scripts,tests}` after all
    edits returns exactly 4 files, all historical/explanatory comments ("R9 step 8
    deleted the legacy app…") with zero live code paths — checked line by line, not just
    counted.
  - MEASURED: `typecheck` clean, `build` clean (bundle actually shrank, 812KB → 791KB,
    despite the new Compose files — the deleted legacy chunk was bigger than what
    replaced it; the separate lazy-loaded `styles-*.css` chunk is gone from the build
    output entirely), `lint:design` 83 files clean (85 → 83: −6 deleted, +4 new Compose
    files). Every existing Playwright suite re-run individually (not batched — an
    earlier batched run threw 11 Stemma failures under heavy concurrent load, same
    known flakiness class R6/R8 already logged; re-ran `test:stemma` alone twice,
    16/16 clean both times) plus the new `#/add` geometry test: `test:fence` 29/29 (+2
    fixme), `test:landing` 9/9, `test:dossier` 6/6, `test:stemma` 16/16, `test:reveal`
    11/11, `test:reveal-choreography` 3/3, `test:chronicle` 8/8, `test:shortcuts` 5/5,
    `test:style` 5/5, `test:reduced-motion` 4/4, `test:geometry` 22/22, `test:unit`
    63/63, backend `pytest` 124/6 (unchanged). Compose screen itself screenshotted at
    1440×900 in both the empty and filled (live "N chapters detected" readout) states —
    renders correctly, on-brand, no console errors.
- **Stopped at:** step 8 of 10 green. Continuing straight into step 9 in this same
  session (no user instruction to stop here).
- **Next:** R9 steps 9-10 (the §16 acceptance checklist line by line, final full suite +
  full 1440×900/1280×720 shoot).
