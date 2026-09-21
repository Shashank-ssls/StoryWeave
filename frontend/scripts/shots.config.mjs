// Per-phase shot lists for scripts/shoot.mjs (FRONTEND_OVERHAUL.md §3 point 4).
// Each phase adds its own entry; nothing here is shared state between phases, so an old
// phase's shots keep working as "before" pictures even after later phases change the app.
//
// Phase 0/1's "library"/"graph"/"*-expected-degraded" shots originally navigated to the
// bare `baseUrl` — before R2 there was no router and the old app WAS the root. Since R2
// the old app lives only at `#/_legacy`, so those shots were retargeted there (R3, Step 1:
// a harness with known-failing configs is not allowed). They still shoot the same old UI
// they always did; only the URL contract moved.
//
// A shot is { name, run(page, baseUrl) }: `run` OWNS its navigation (calls page.goto
// itself) rather than relying on a shared pre-navigation from the harness — a same-origin
// URL that differs only in the hash does NOT reload the page, so a shot for a hash route
// (e.g. #/_type) needs its own full `page.goto` to actually re-run main.tsx's route check.

/** @typedef {{ name: string, expectedConsoleErrors?: string[], run: (page: import('@playwright/test').Page, baseUrl: string) => Promise<void> }} Shot */

/** @param {string} phase @returns {Promise<Shot[]>} */
export async function getShots(phase) {
  switch (phase) {
    case "0":
      return [
        {
          name: "library",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/_legacy`, { waitUntil: "networkidle" });
            await page.waitForSelector(".lib-shelf", { timeout: 10_000 });
          },
        },
        {
          name: "graph",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/_legacy`, { waitUntil: "networkidle" });
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
            await page.goto(`${baseUrl}/#/_legacy`, { waitUntil: "networkidle" });
            await page.waitForSelector(".lib-shelf", { timeout: 10_000 });
          },
        },
        {
          name: "graph-expected-degraded",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/_legacy`, { waitUntil: "networkidle" });
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
    case "3": {
      // R3 — chapter model + fence. All shots on the Hollow Crown demo (4 chapters).
      const SLUG = "the-hollow-crown";
      const KEY = `storyweave:bookmark:${SLUG}`;
      const GRAPH_RE = /\/api\/v1\/works\/[^/]+\/graph\?n=\d+/;
      const nOf = (url) => Number(/[?&]n=(\d+)/.exec(url)?.[1]);
      /** Fresh dossier at a given stored bookmark. */
      const atChapter = async (page, baseUrl, n) => {
        await page.goto(`${baseUrl}/#/work/${SLUG}/entity/1`, { waitUntil: "networkidle" });
        await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)]);
        await page.reload({ waitUntil: "networkidle" });
        await page.waitForSelector(`[data-testid="chapter-row-bookmark"][data-chapter="${n}"]`);
      };
      const confirm = async (page, n) => {
        await page.click('[data-testid="change-chapter"]');
        await page.fill('[data-testid="chapter-input"]', String(n));
        await page.click('[data-testid="set-bookmark"]');
      };
      return [
        { name: "rail-ch1", run: (p, b) => atChapter(p, b, 1) },
        { name: "rail-ch2", run: (p, b) => atChapter(p, b, 2) },
        { name: "rail-ch4", run: (p, b) => atChapter(p, b, 4) },
        {
          name: "stemma-rail-ch2",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 2);
            await page.goto(`${baseUrl}/#/work/${SLUG}/web`, { waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="chapter-row-bookmark"][data-chapter="2"]');
          },
        },
        {
          name: "dialog-default",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 3);
            await page.click('[data-testid="change-chapter"]');
            await page.waitForSelector('[data-testid="chapter-dialog"]');
          },
        },
        {
          name: "dialog-invalid",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 3);
            await page.click('[data-testid="change-chapter"]');
            await page.fill('[data-testid="chapter-input"]', "2000");
            await page.waitForSelector('[data-testid="chapter-invalid"]:not([hidden])');
          },
        },
        {
          name: "loading-after-confirm",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 3);
            // Hold the n=4 response so the wash is on screen when the shot is taken.
            await page.route(GRAPH_RE, async (route) => {
              if (nOf(route.request().url()) === 4) await new Promise((r) => setTimeout(r, 4000));
              await route.continue();
            });
            await confirm(page, 4);
            await page.waitForSelector('[data-testid="loading-wash"]');
          },
        },
        {
          name: "error-banner",
          // Chrome's own log line for the injected 500 — see shoot.mjs.
          expectedConsoleErrors: [
            "Failed to load resource: the server responded with a status of 500 (Internal Server Error)",
          ],
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 3);
            await page.route(GRAPH_RE, async (route) => {
              if (nOf(route.request().url()) === 4) await route.fulfill({ status: 500, body: "boom" });
              else await route.continue();
            });
            await confirm(page, 4);
            await page.waitForSelector('[data-testid="error-banner"]');
          },
        },
        {
          name: "toast-forward",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 3);
            await confirm(page, 4);
            await page.waitForSelector('[data-testid="toast"][data-kind="forward"]');
          },
        },
        {
          name: "toast-backward",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 3);
            await page.keyboard.press("[");
            await page.waitForSelector('[data-testid="toast"][data-kind="backward"]');
          },
        },
      ];
    }
    default:
      throw new Error(`No shots defined for phase "${phase}" yet — add one to shots.config.mjs.`);
  }
}
