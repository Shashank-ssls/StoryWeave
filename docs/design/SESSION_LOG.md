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
- **Commits:** 782998b → b475ded (R7) → (R8 commit; see `git log`)
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
