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
            // Since R5 the Stemma rail follows §6.3: the bookmark shows in the footer
            // ("Read to Chapter II of 4 · change"), not as R3's compact list.
            await page.waitForSelector('[data-testid="stemma-footer"]');
            await page.waitForFunction(() => document.querySelector('[data-testid="stemma-footer"]')?.textContent?.includes("Chapter II of 4"));
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
    case "4": {
      // R4 — Dossier. Real demo data except the clearly-named synthetic fixture shot.
      const SLUG = "the-hollow-crown";
      const KEY = `storyweave:bookmark:${SLUG}`;
      const GRAPH_RE = /\/api\/v1\/works\/[^/]+\/graph\?n=\d+/;
      const nOf = (url) => Number(/[?&]n=(\d+)/.exec(url)?.[1]);
      const dossierAt = async (page, baseUrl, n, entity = "1") => {
        await page.goto(`${baseUrl}/#/work/${SLUG}/entity/${entity}`, { waitUntil: "networkidle" });
        await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)]);
        await page.reload({ waitUntil: "networkidle" });
        await page.waitForSelector('[data-testid="entity-main"], [data-testid="state-not-present"]');
        await page.waitForTimeout(600); // ego layout + n−1 tags
      };
      return [
        { name: "dossier-wren-ch1", run: (p, b) => dossierAt(p, b, 1) },
        { name: "dossier-wren-ch2", run: (p, b) => dossierAt(p, b, 2) },
        { name: "dossier-wren-ch3", run: (p, b) => dossierAt(p, b, 3) },
        { name: "dossier-wren-ch4", run: (p, b) => dossierAt(p, b, 4) },
        // Ser Dunmore (9): a person with no identity edge — no identity block, no red.
        { name: "dossier-dunmore-ch4", run: (p, b) => dossierAt(p, b, 4, "9") },
        // Lady Veris (12) at chapter 2: not met yet → §6.7 card.
        { name: "dossier-not-present", run: (p, b) => dossierAt(p, b, 2, "12") },
        {
          name: "dossier-skeleton",
          async run(page, baseUrl) {
            await page.route(GRAPH_RE, async (route) => {
              await new Promise((r) => setTimeout(r, 5000));
              await route.continue();
            });
            await page.goto(`${baseUrl}/#/work/${SLUG}/entity/1`);
            await page.waitForSelector('[data-testid="skeleton"]');
          },
        },
        {
          name: "dossier-synthetic-100",
          async run(page, baseUrl) {
            const fs = await import("node:fs");
            const synthetic = JSON.parse(fs.readFileSync(new URL("../tests/fixtures/synthetic-100.json", import.meta.url), "utf8"));
            await page.route(GRAPH_RE, async (route) => {
              const n = nOf(route.request().url());
              const fenced = {
                slug: SLUG, n,
                elements: {
                  nodes: synthetic.elements.nodes.filter((x) => x.data.revealed_chapter <= n),
                  edges: synthetic.elements.edges.filter((x) => x.data.revealed_chapter <= n),
                },
              };
              await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced) });
            });
            await page.goto(`${baseUrl}/#/work/${SLUG}`, { waitUntil: "networkidle" });
            await page.evaluate((k) => localStorage.setItem(k, "4"), KEY);
            await page.reload({ waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="entity-main"]');
            await page.waitForTimeout(800);
          },
        },
      ];
    }
    case "5": {
      // R5 — The Stemma. Demo data unless named synthetic.
      const SLUG = "the-hollow-crown";
      const KEY = `storyweave:bookmark:${SLUG}`;
      const GRAPH_RE = /\/api\/v1\/works\/[^/]+\/graph\?n=\d+/;
      const nOf = (url) => Number(/[?&]n=(\d+)/.exec(url)?.[1]);
      const stemmaAt = async (page, baseUrl, n, focus) => {
        await page.goto(`${baseUrl}/#/work/${SLUG}/web${focus ? `?focus=${focus}` : ""}`, { waitUntil: "networkidle" });
        await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)]);
        await page.reload({ waitUntil: "networkidle" });
        await page.waitForSelector('[data-testid="stemma-cy"]');
        await page.waitForTimeout(2200); // cola burst + fit
      };
      const emit = (page, id, ev) => page.evaluate(([i, e]) => window.__storyweaveCy.stemma.getElementById(i).emit(e), [id, ev]);
      const zoomTo = (page, z) => page.evaluate((zz) => { const cy = window.__storyweaveCy.stemma; cy.zoom({ level: zz, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }); }, z);
      const synthetic = async (page) => {
        const fs = await import("node:fs");
        const data = JSON.parse(fs.readFileSync(new URL("../tests/fixtures/synthetic-100.json", import.meta.url), "utf8"));
        await page.route(GRAPH_RE, async (route) => {
          const n = nOf(route.request().url());
          const fenced = { slug: SLUG, n, elements: { nodes: data.elements.nodes.filter((x) => x.data.revealed_chapter <= n), edges: data.elements.edges.filter((x) => x.data.revealed_chapter <= n) } };
          await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced) });
        });
      };
      return [
        { name: "stemma-unfocused", async run(p, b) { await stemmaAt(p, b, 3); await p.click('[data-testid="clear-focus"]'); await p.waitForTimeout(600); } },
        { name: "stemma-focus-1step", run: (p, b) => stemmaAt(p, b, 3) },
        { name: "stemma-focus-2steps", async run(p, b) { await stemmaAt(p, b, 3); await p.click('[data-testid="steps-2"]'); await p.waitForTimeout(600); } },
        { name: "stemma-edge-identity", async run(p, b) { await stemmaAt(p, b, 3); await emit(p, "e12", "tap"); await p.waitForTimeout(300); } },
        { name: "stemma-edge-social", async run(p, b) { await stemmaAt(p, b, 3); await p.click('[data-testid="cast-everyone"]'); await p.waitForTimeout(1400); await emit(p, "e1", "tap"); await p.waitForTimeout(300); } },
        { name: "stemma-node-selected", async run(p, b) { await stemmaAt(p, b, 3, "7"); } },
        { name: "stemma-zoom-far", async run(p, b) { await stemmaAt(p, b, 4); await p.click('[data-testid="cast-everyone"]'); await p.waitForTimeout(1400); await zoomTo(p, 0.4); await p.waitForTimeout(300); } },
        { name: "stemma-zoom-close", async run(p, b) { await stemmaAt(p, b, 3); await zoomTo(p, 1.8); await p.waitForTimeout(300); } },
        { name: "stemma-no-match", async run(p, b) { await stemmaAt(p, b, 2); await p.fill('[data-testid="stemma-search"]', "Veris"); await p.waitForSelector('[data-testid="search-no-match"]'); } },
        { name: "stemma-synthetic-principal", async run(p, b) { await synthetic(p); await stemmaAt(p, b, 4); await p.click('[data-testid="clear-focus"]'); await p.waitForTimeout(700); } },
        { name: "stemma-synthetic-everyone", async run(p, b) { await synthetic(p); await stemmaAt(p, b, 4); await p.click('[data-testid="cast-everyone"]'); await p.waitForTimeout(1400); await p.click('[data-testid="clear-focus"]'); await p.waitForTimeout(700); } },
        { name: "stemma-ch1", run: (p, b) => stemmaAt(p, b, 1) },
        { name: "stemma-ch2", run: (p, b) => stemmaAt(p, b, 2) },
        { name: "stemma-ch3-everyone", async run(p, b) { await stemmaAt(p, b, 3); await p.click('[data-testid="cast-everyone"]'); await p.waitForTimeout(1400); } },
        { name: "stemma-ch4", run: (p, b) => stemmaAt(p, b, 4) },
      ];
    }
    case "6": {
      // R6 — Reveal moment. Normal / deepening / pager page 2 / summary sheet / quiet
      // toast on real Hollow Crown demo data; the Dossier replay button + the Stemma's
      // .just-revealed mid-glow.
      const SLUG = "the-hollow-crown";
      const KEY = `storyweave:bookmark:${SLUG}`;
      const GRAPH_RE = /\/api\/v1\/works\/[^/]+\/graph\?n=\d+/;
      const nOf = (url) => Number(/[?&]n=(\d+)/.exec(url)?.[1]);
      const atChapter = async (page, baseUrl, n, entity = "1") => {
        await page.goto(`${baseUrl}/#/work/${SLUG}/entity/${entity}`, { waitUntil: "networkidle" });
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
        {
          name: "reveal-normal",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 1);
            await confirm(page, 2);
            await page.waitForSelector('[data-testid="reveal-overlay"]');
            await page.waitForTimeout(1500); // let the choreography finish
          },
        },
        {
          name: "reveal-deepening",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 3);
            await confirm(page, 4);
            await page.waitForSelector('[data-testid="reveal-overlay"]');
            await page.waitForTimeout(1500);
          },
        },
        {
          name: "reveal-pager-page2",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 1);
            await confirm(page, 4);
            await page.waitForSelector('[data-testid="reveal-pager"]');
            await page.waitForTimeout(1500);
            await page.click('[data-testid="reveal-pager-next"]');
            await page.waitForTimeout(1500);
          },
        },
        {
          name: "reveal-summary-sheet",
          async run(page, baseUrl) {
            const fs = await import("node:fs");
            const synthetic = JSON.parse(fs.readFileSync(new URL("../tests/fixtures/synthetic-100.json", import.meta.url), "utf8"));
            await page.route(GRAPH_RE, async (route) => {
              const n = nOf(route.request().url());
              const fenced = {
                slug: SLUG, n,
                elements: {
                  nodes: synthetic.elements.nodes.filter((x) => x.data.revealed_chapter <= n),
                  edges: synthetic.elements.edges.filter((x) => x.data.revealed_chapter <= n),
                },
              };
              await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced) });
            });
            await atChapter(page, baseUrl, 1);
            await confirm(page, 4);
            await page.waitForSelector('[data-testid="reveal-summary-sheet"]');
          },
        },
        {
          name: "reveal-quiet-toast",
          async run(page, baseUrl) {
            await page.goto(`${baseUrl}/#/work/${SLUG}/entity/1`, { waitUntil: "networkidle" });
            await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "1"]);
            await page.evaluate(() => localStorage.setItem("storyweave:revealQuiet", "1"));
            await page.reload({ waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="chapter-row-bookmark"][data-chapter="1"]');
            await confirm(page, 2);
            await page.waitForSelector('[data-testid="reveal-quiet-toast"]');
          },
        },
        {
          name: "dossier-identity-replay",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 2);
            await page.waitForSelector('[data-testid="identity-block"]');
            await page.waitForTimeout(400);
          },
        },
        {
          name: "stemma-just-revealed",
          async run(page, baseUrl) {
            await atChapter(page, baseUrl, 1);
            await confirm(page, 2);
            await page.waitForSelector('[data-testid="reveal-overlay"]');
            await page.waitForTimeout(1500);
            // "Return to The Stemma" closes the overlay AND navigates there, triggering
            // the .just-revealed pulse on the same edge the overlay was showing.
            await page.click('[data-testid="reveal-return"]');
            await page.waitForSelector('[data-testid="stemma-cy"]');
            await page.waitForTimeout(2200); // cola burst + camera fit settle (R5 convention)
          },
        },
      ];
    }
    case "7": {
      // R7 — Chronicle. Small-N (real demo, 4 chapters) + a synthetic large-N book to
      // exercise the proportional-columns/blocks-of-50 fallback path (§6.4 scaling rule).
      const SLUG = "the-hollow-crown";
      const KEY = `storyweave:bookmark:${SLUG}`;
      const GRAPH_RE = /\/api\/v1\/works\/[^/]+\/graph\?n=\d+/;
      const chronicleAt = async (page, baseUrl, n) => {
        await page.goto(`${baseUrl}/#/work/${SLUG}/chronicle`, { waitUntil: "networkidle" });
        await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)]);
        await page.reload({ waitUntil: "networkidle" });
        await page.waitForSelector('[data-testid="chronicle-svg"]');
        await page.waitForTimeout(300);
      };
      return [
        { name: "chronicle-ch1", run: (p, b) => chronicleAt(p, b, 1) },
        { name: "chronicle-ch2", run: (p, b) => chronicleAt(p, b, 2) },
        { name: "chronicle-ch3", run: (p, b) => chronicleAt(p, b, 3) },
        { name: "chronicle-ch4", run: (p, b) => chronicleAt(p, b, 4) },
        {
          name: "chronicle-everyone",
          async run(page, baseUrl) {
            await chronicleAt(page, baseUrl, 4);
            await page.click('[data-testid="chronicle-cast-everyone"]');
            await page.waitForTimeout(200);
          },
        },
        {
          name: "chronicle-dialog",
          async run(page, baseUrl) {
            await chronicleAt(page, baseUrl, 3);
            await page.click('[data-testid="chronicle-read-on"]');
            await page.waitForSelector('[data-testid="chapter-dialog"]');
          },
        },
        {
          name: "chronicle-large-n",
          async run(page, baseUrl) {
            // A small synthetic book spread over 40 chapters — enough to cross the
            // small-N/large-N boundary (>12) and exercise the blocks-of-50 header.
            const nodes = [];
            const edges = [];
            for (let i = 1; i <= 10; i++) {
              const chapter = 1 + (i - 1) * 4;
              nodes.push({ data: { id: String(i), label: `Character ${i}`, type: "Character", subtype: "Person", importance: 0.5, first_seen_chapter: chapter, revealed_chapter: chapter, extraction_method: "gliner", evidence_span: "x", properties: {} } });
            }
            edges.push({ data: { id: "se1", source: "1", target: "2", relation: "Ally", tier: 2, first_seen_chapter: 5, revealed_chapter: 5, extraction_method: "rule", evidence_span: "x" } });
            edges.push({ data: { id: "se2", source: "3", target: "4", relation: "SECRET_IDENTITY", tier: 3, first_seen_chapter: 30, revealed_chapter: 30, extraction_method: "llm", evidence_span: "the two were one" } });
            await page.route(/\/api\/v1\/works$/, async (route) => {
              await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ works: [{ id: 1, slug: SLUG, title: "The Hollow Crown", chapter_count: 40 }] }) });
            });
            await page.route(GRAPH_RE, async (route) => {
              const n = Number(/[?&]n=(\d+)/.exec(route.request().url())?.[1]);
              const fenced = { slug: SLUG, n, elements: { nodes: nodes.filter((x) => x.data.revealed_chapter <= n), edges: edges.filter((x) => x.data.revealed_chapter <= n) } };
              await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced) });
            });
            await page.goto(`${baseUrl}/#/work/${SLUG}/chronicle`, { waitUntil: "networkidle" });
            await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "37"]);
            await page.reload({ waitUntil: "networkidle" });
            await page.waitForSelector('[data-testid="chronicle-svg"]');
            await page.waitForTimeout(400);
          },
        },
      ];
    }
    default:
      throw new Error(`No shots defined for phase "${phase}" yet — add one to shots.config.mjs.`);
  }
}
