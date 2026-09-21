// Per-phase shot lists for scripts/shoot.mjs (FRONTEND_OVERHAUL.md §3 point 4).
// Each phase adds its own entry; nothing here is shared state between phases, so an old
// phase's shots keep working as "before" pictures even after later phases change the app.
//
// A shot is { name, run(page) }: `run` drives the page (old app has no router, so phase 0
// shots are plain interactions; later phases with hash routing will `page.goto` a route).

/** @typedef {{ name: string, run: (page: import('@playwright/test').Page) => Promise<void> }} Shot */

/** @param {string} phase @returns {Promise<Shot[]>} */
export async function getShots(phase) {
  switch (phase) {
    case "0":
      return [
        {
          name: "library",
          async run(page) {
            await page.waitForSelector(".lib-shelf", { timeout: 10_000 });
          },
        },
        {
          name: "graph",
          async run(page) {
            await page.click(".work-card-open");
            await page.waitForSelector(".graph-canvas", { timeout: 10_000 });
            // cola physics settle time (see memory/screenshot-gate-workflow.md).
            await page.waitForTimeout(2_500);
          },
        },
      ];
    default:
      throw new Error(`No shots defined for phase "${phase}" yet — add one to shots.config.mjs.`);
  }
}
