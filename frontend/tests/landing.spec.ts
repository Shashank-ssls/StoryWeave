// Landing (DESIGN_SPEC §6.1, §6.7) end-to-end: the try-it panel's mini-graph must obey
// the fence exactly like every other screen (F9), stepping forward/backward goes through
// the same commit path as everywhere else (including the real R6 reveal), and each state
// card is reachable via route interception.

import { test, expect, type Page, type Route } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { recordGraphRequests, assertNoGraphRequestAbove, dismissRevealIfShown, GRAPH_ROUTE_RE } from "./fenceHelpers";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SLUG = "the-hollow-crown";
const KEY = `storyweave:bookmark:${SLUG}`;

interface Node { id: string; type: string }
interface Payload { elements: { nodes: { data: Node }[]; edges: { data: unknown }[] } }
const DRAWN = new Set(["Character", "Organization", "Place", "Item", "Ability"]);
const fixture = (n: number): Payload =>
  JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "hollow-crown", `graph-n${n}.json`), "utf8")) as Payload;

async function landingAt(page: Page, n: number): Promise<void> {
  await page.goto("/#/");
  await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)] as const);
  await page.reload();
  await page.waitForSelector('[data-testid="landing-mini-graph"]');
  await page.waitForTimeout(300);
}

test.describe("Landing (§6.1) — try-it panel obeys the fence", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#/");
    await page.evaluate((k) => localStorage.removeItem(k), KEY);
  });

  test("F9 — the mini-graph draws only the current chapter's fenced nodes, at every chapter", async ({ page }) => {
    const log = recordGraphRequests(page);
    for (const n of [1, 2, 3, 4]) {
      await landingAt(page, n);
      const exp = fixture(n).elements.nodes.filter((x) => DRAWN.has(x.data.type)).map((x) => x.data.id).sort();
      const got = (await page.locator('[data-testid="landing-mini-graph"]').getAttribute("data-nodes"))?.split(",").filter(Boolean).sort() ?? [];
      expect(got, `mini-graph nodes @${n}`).toEqual(exp);
      assertNoGraphRequestAbove(log, n);
    }
    await test.info().attach("graph-requests", { body: JSON.stringify(log.urls, null, 2), contentType: "application/json" });
  });

  test("F2 — no text on the page ever names a later-chapter-only entity", async ({ page }) => {
    await landingAt(page, 1);
    const text = await page.evaluate(() => document.body.innerText);
    expect(text).not.toContain("Prince Caelum"); // first appears ch.2
    expect(text).not.toContain("Lady Veris"); // first appears ch.3
  });

  test("stepper forward crosses a reveal and plays the real overlay; backward shows the sealed-again toast", async ({ page }) => {
    await landingAt(page, 1);
    await page.click('[data-testid="stepper-next"]');
    await expect(page.locator('[data-testid="reveal-overlay"]')).toBeVisible();
    await dismissRevealIfShown(page);
    await expect(page.locator('[data-testid="stepper-current"][data-chapter="2"]')).toBeVisible();
    await expect(page.locator('[data-testid="explore-full-book"]')).toBeVisible();
    // backward: a "read" chapter-1 button steps back with no reveal, sealed-again toast
    await page.click('[data-testid="stepper-read"][data-chapter="1"]');
    await expect(page.locator('[data-testid="toast"][data-kind="backward"]')).toBeVisible();
  });

  test('"Explore the full book" opens the real Dossier at the same bookmark', async ({ page }) => {
    await landingAt(page, 3);
    await dismissRevealIfShown(page);
    await page.click('[data-testid="explore-full-book"]');
    await expect(page.locator('[data-testid="dossier-root"]')).toBeVisible();
    await expect(page.locator('[data-testid="chapter-row-bookmark"]')).toHaveAttribute("data-chapter", "3");
  });
});

test.describe("Landing — state cards (§6.7)", () => {
  test("empty shelf: 0 works shows both the footer empty-shelf card and the try-it demo-missing card", async ({ page }) => {
    await page.route(/\/api\/v1\/works$/, async (route: Route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ works: [] }) });
    });
    await page.goto("/#/");
    await expect(page.locator('[data-testid="state-empty-shelf"]')).toBeVisible();
    await expect(page.locator('[data-testid="state-demo-missing"]')).toBeVisible();
    await expect(page.locator('[data-testid="open-sample"]')).toBeVisible();
    await expect(page.locator('[data-testid="add-novel-empty"]')).toBeVisible();
  });

  test("demo missing specifically: works present but none is the demo slug", async ({ page }) => {
    await page.route(/\/api\/v1\/works$/, async (route: Route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ works: [{ id: 9, slug: "some-other-book", title: "Some Other Book", chapter_count: 12 }] }) });
    });
    await page.goto("/#/");
    await expect(page.locator('[data-testid="state-demo-missing"]')).toBeVisible();
    await expect(page.locator('[data-testid="landing-shelf"]')).toBeVisible(); // the shelf itself still lists real works
    await expect(page.locator('[data-testid="state-empty-shelf"]')).toHaveCount(0);
  });

  test("error: /works unreachable shows the error card in both the try-it panel and the footer", async ({ page }) => {
    await page.route(/\/api\/v1\/works$/, async (route: Route) => {
      await route.fulfill({ status: 500, body: "boom" });
    });
    await page.goto("/#/");
    await expect(page.locator('[data-testid="state-try-it-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="state-shelf-error"]')).toBeVisible();
  });

  test('"How the seal works" opens the explainer panel; Esc closes it', async ({ page }) => {
    await page.goto("/#/");
    await page.click('[data-testid="how-seal-works"]');
    await expect(page.locator('[data-testid="explainer-panel"]')).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="explainer-panel"]')).toHaveCount(0);
  });
});

test.describe("Landing — fonts loading (no layout shift)", () => {
  test("cumulative layout shift stays at or below 2% through first paint", async ({ page }) => {
    await page.goto("/#/");
    await page.waitForSelector('[data-testid="landing-mini-graph"]');
    await page.waitForTimeout(500);
    const cls = await page.evaluate(
      () =>
        new Promise<number>((resolve) => {
          let total = 0;
          try {
            new PerformanceObserver((list) => {
              for (const entry of list.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[]) {
                if (!entry.hadRecentInput) total += entry.value;
              }
            }).observe({ type: "layout-shift", buffered: true });
          } catch {
            /* layout-shift unsupported in this engine — nothing to report */
          }
          setTimeout(() => resolve(total), 200);
        }),
    );
    expect(cls).toBeLessThanOrEqual(0.02);
  });
});
