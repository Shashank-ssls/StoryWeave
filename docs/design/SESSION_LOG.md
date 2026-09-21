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
