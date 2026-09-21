// Per-phase shot lists for scripts/shoot.mjs (FRONTEND_OVERHAUL.md §3 point 4).
// Each phase adds its own entry; nothing here is shared state between phases, so an old
// phase's shots keep working as "before" pictures even after later phases change the app.
//
// EXCEPTION: phase 0/1's "library"/"graph"/"*-expected-degraded" shots navigate to the
// bare `baseUrl` (no hash) expecting the OLD app there, because before R2 there was no
// router and the old app WAS the root. As of R2 the bare URL resolves to the new
// `#/` (Landing) route instead — the old app only lives at `#/_legacy` now. Re-running
// `--phase=0`/`--phase=1` today will therefore fail at that step; this is correct,
// expected behaviour (R2's whole point), not a regression. Phase 2's own "legacy" shot is
// the up-to-date equivalent. Phase 0/1's configs are left as-is, frozen, as an honest
// record of what was shot at the time rather than silently rewritten to still "pass".
//
// A shot is { name, run(page, baseUrl) }: `run` OWNS its navigation (calls page.goto
// itself) rather than relying on a shared pre-navigation from the harness — a same-origin
// URL that differs only in the hash does NOT reload the page, so a shot for a hash route
// (e.g. #/_type) needs its own full `page.goto` to actually re-run main.tsx's route check.

/** @typedef {{ name: string, run: (page: import('@playwright/test').Page, baseUrl: string) => Promise<void> }} Shot */

/** @param {string} phase @returns {Promise<Shot[]>} */
export async function getShots(phase) {
  switch (phase) {
    case "0":
      return [
        {
          name: "library",
          async run(page, baseUrl) {
            await page.goto(baseUrl, { waitUntil: "networkidle" });
            await page.waitForSelector(".lib-shelf", { timeout: 10_000 });
          },
        },
        {
          name: "graph",
          async run(page, baseUrl) {
            await page.goto(baseUrl, { waitUntil: "networkidle" });
            await page.click(".work-card-open");
            await page.waitForSelector(".graph-canvas", { timeout: 10_000 });
            // cola physics settle time (see memory/screenshot-gate-workflow.md).
            await page.waitForTimeout(2_500);
          },
        },
      ];
    case "1":
      return [
        {
          name: "type-scale",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/_type`, { waitUntil: "networkidle" });
            await page.waitForSelector(".type-page");
          },
        },
        // "expected-degraded" — record only, not something to fix (FRONTEND_OVERHAUL §1 /
        // R1 scope: old fonts/palette removed, old screens are allowed to look wrong).
        {
          name: "library-expected-degraded",
          async run(page, baseUrl) {
            await page.goto(baseUrl, { waitUntil: "networkidle" });
            await page.waitForSelector(".lib-shelf", { timeout: 10_000 });
          },
        },
        {
          name: "graph-expected-degraded",
          async run(page, baseUrl) {
            await page.goto(baseUrl, { waitUntil: "networkidle" });
            await page.click(".work-card-open");
            await page.waitForSelector(".graph-canvas", { timeout: 10_000 });
            await page.waitForTimeout(2_500);
          },
        },
      ];
    case "2": {
      const DEMO_SLUG = "the-hollow-crown"; // real backend data — proves the live /works fetch
      return [
        {
          name: "landing",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/`, { waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="landing-root"]');
          },
        },
        {
          name: "dossier",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/work/${DEMO_SLUG}/entity/1`, { waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="dossier-root"]');
          },
        },
        {
          name: "stemma",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/work/${DEMO_SLUG}/web`, { waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="stemma-root"]');
          },
        },
        {
          name: "chronicle",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/work/${DEMO_SLUG}/chronicle`, { waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="chronicle-root"]');
          },
        },
        {
          name: "type-scale",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/_type`, { waitUntil: "networkidle" });
            await page.waitForSelector(".type-page");
          },
        },
        {
          name: "legacy",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/_legacy`, { waitUntil: "networkidle" });
            await page.waitForSelector(".lib-shelf", { timeout: 10_000 });
          },
        },
      ];
    }
    default:
      throw new Error(`No shots defined for phase "${phase}" yet — add one to shots.config.mjs.`);
  }
}
