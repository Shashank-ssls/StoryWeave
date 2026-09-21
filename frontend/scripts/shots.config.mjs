// Per-phase shot lists for scripts/shoot.mjs (FRONTEND_OVERHAUL.md §3 point 4).
// Each phase adds its own entry; nothing here is shared state between phases, so an old
// phase's shots keep working as "before" pictures even after later phases change the app.
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
    default:
      throw new Error(`No shots defined for phase "${phase}" yet — add one to shots.config.mjs.`);
  }
}
