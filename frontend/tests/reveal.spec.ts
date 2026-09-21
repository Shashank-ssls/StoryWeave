// The Reveal moment (DESIGN_SPEC §6.5, §8.2) + the R6 open-question RESOLUTION
// (FRONTEND_OVERHAUL.md §9): identity diffing is keyed by the unordered entity pair, so
// Wren/Caelum's SECRET_IDENTITY -> TRANSMIGRATED_INTO swap at chapter 4 plays as a
// DEEPENING reveal of the chapter-2 reveal, never a duplicate. Every scenario here is
// exercised against the REAL Hollow Crown demo data (R0 fixtures), so what the overlay
// shows is checked against the actual fenced payload, not a mock.

import { test, expect, type Page, type Route } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { recordGraphRequests, assertNoGraphRequestAbove, GRAPH_ROUTE_RE, type GraphRequestLog } from "./fenceHelpers";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SLUG = "the-hollow-crown";
const KEY = `storyweave:bookmark:${SLUG}`;
const QUIET_KEY = "storyweave:revealQuiet";
const GRAPH_RE = /\/api\/v1\/works\/[^/]+\/graph\?n=\d+/;

interface Payload { elements: { nodes: { data: { id: string; label: string } }[]; edges: unknown[] } }
const fixture = (n: number): Payload =>
  JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "hollow-crown", `graph-n${n}.json`), "utf8")) as Payload;
const labelOf = (n: number, id: string): string =>
  fixture(n).elements.nodes.find((x) => x.data.id === id)!.data.label;

function nOf(url: string): number {
  return Number(/[?&]n=(\d+)/.exec(url)?.[1]);
}

async function fresh(page: Page): Promise<void> {
  await page.goto("/#/");
  await page.evaluate((k) => localStorage.removeItem(k), KEY);
  await page.evaluate((k) => localStorage.removeItem(k), QUIET_KEY);
}
async function atChapter(page: Page, n: number, entity = "1"): Promise<void> {
  await page.goto(`/#/work/${SLUG}/entity/${entity}`);
  await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)] as const);
  await page.reload();
  await page.waitForSelector(`[data-testid="chapter-row-bookmark"][data-chapter="${n}"]`);
}
async function confirmChapter(page: Page, n: number): Promise<void> {
  await page.click('[data-testid="change-chapter"]');
  await page.fill('[data-testid="chapter-input"]', String(n));
  await page.click('[data-testid="set-bookmark"]');
}
const overlay = (page: Page) => page.locator('[data-testid="reveal-overlay"]');
const summarySheet = (page: Page) => page.locator('[data-testid="reveal-summary-sheet"]');
const quietToast = (page: Page) => page.locator('[data-testid="reveal-quiet-toast"]');

async function noRevealUiAppeared(page: Page): Promise<void> {
  await page.waitForTimeout(600);
  expect(await overlay(page).count()).toBe(0);
  expect(await summarySheet(page).count()).toBe(0);
  expect(await quietToast(page).count()).toBe(0);
}

test.describe("Reveal moment (DESIGN_SPEC §6.5, §8.2)", () => {
  test.beforeEach(async ({ page }) => {
    await fresh(page);
  });

  test("1→2: a NORMAL reveal for Wren/Caelum — headline, quote and kicker all come from the fenced n=2 payload, no 'Before' line", async ({ page }) => {
    await atChapter(page, 1);
    await confirmChapter(page, 2);
    await expect(overlay(page)).toBeVisible();
    await expect(overlay(page)).toHaveAttribute("data-kind", "normal");
    await expect(page.locator('[data-testid="reveal-kicker"]')).toContainText("Chapter II");
    await expect(page.locator('[data-testid="reveal-kicker"]')).toContainText("Rubric · a hidden name");
    const headline = await page.locator('[data-testid="reveal-headline"]').innerText();
    expect(headline).toContain(labelOf(2, "1")); // "Wren"
    expect(headline).toContain(labelOf(2, "7")); // "Prince Caelum"
    await expect(page.locator('[data-testid="reveal-quote"]')).toContainText("Wren was Caelum.");
    expect(await page.locator('[data-testid="reveal-before"]').count()).toBe(0);
    expect(await page.locator('[data-testid="reveal-pager"]').count()).toBe(0); // single reveal, no pager

    // §8.2: on close, the identity block gets a 3s highlight.
    await page.keyboard.press("Escape");
    await expect(overlay(page)).toHaveCount(0);
    const block = page.locator('[data-testid="identity-block"][data-edge="e12"]');
    await expect(block).toHaveClass(/justRevealed/);
    await page.waitForTimeout(3200);
    await expect(block).not.toHaveClass(/justRevealed/);
  });

  test("2→3: a NORMAL reveal for Sparrow/Veris; DOM text is fenced-only (no chapter-4-only names)", async ({ page }) => {
    await atChapter(page, 2);
    await confirmChapter(page, 3);
    await expect(overlay(page)).toBeVisible();
    await expect(overlay(page)).toHaveAttribute("data-kind", "normal");
    const headline = await page.locator('[data-testid="reveal-headline"]').innerText();
    expect(headline).toContain(labelOf(3, "11"));
    expect(headline).toContain(labelOf(3, "12"));
    await expect(page.locator('[data-testid="reveal-quote"]')).toContainText("the Sparrow and Veris were one");
    expect(await page.locator('[data-testid="reveal-before"]').count()).toBe(0);
  });

  test("3→4: a DEEPENING reveal for Wren/Caelum — new relation's copy + quote, 'Before' line names the ch.2 relation", async ({ page }) => {
    await atChapter(page, 3);
    await confirmChapter(page, 4);
    await expect(overlay(page)).toBeVisible();
    await expect(overlay(page)).toHaveAttribute("data-kind", "deepen");
    await expect(page.locator('[data-testid="reveal-kicker"]')).toContainText("Chapter IV");
    await expect(page.locator('[data-testid="reveal-kicker"]')).toContainText("Rubric · the truth deepens");
    const headline = await page.locator('[data-testid="reveal-headline"]').innerText();
    expect(headline).toContain(labelOf(4, "1"));
    expect(headline).toContain(labelOf(4, "7"));
    expect(headline.toLowerCase()).toContain("now lives on as"); // TRANSMIGRATED_INTO copy
    await expect(page.locator('[data-testid="reveal-quote"]')).toContainText("an older soul, drowned prince");
    const before = page.locator('[data-testid="reveal-before"]');
    await expect(before).toBeVisible();
    await expect(before).toContainText("Before:");
    await expect(before).toContainText("Chapter II"); // e12's own revealed_chapter
    expect((await before.innerText()).toLowerCase()).not.toContain("now lives on as"); // the OLD (SECRET_IDENTITY) copy, not the new one
  });

  test("1→4 (jump over the deepening step): both pairs surface as NORMAL reveals with a pager, no 'Before' line on either page", async ({ page }) => {
    await atChapter(page, 1);
    await confirmChapter(page, 4);
    await expect(overlay(page)).toBeVisible();
    await expect(page.locator('[data-testid="reveal-pager-label"]')).toHaveText("1 of 2");
    await expect(overlay(page)).toHaveAttribute("data-kind", "normal");
    expect(await page.locator('[data-testid="reveal-before"]').count()).toBe(0);
    await page.click('[data-testid="reveal-pager-next"]');
    await expect(page.locator('[data-testid="reveal-pager-label"]')).toHaveText("2 of 2");
    await expect(overlay(page)).toHaveAttribute("data-kind", "normal"); // still normal — no intermediate state was ever seen
    expect(await page.locator('[data-testid="reveal-before"]').count()).toBe(0);
    await expect(page.locator('[data-testid="reveal-pager-next"]')).toBeDisabled();
    await page.click('[data-testid="reveal-pager-prev"]');
    await expect(page.locator('[data-testid="reveal-pager-label"]')).toHaveText("1 of 2");
  });

  test("4→2 (backward): no reveal UI fires; the 'sealed again' toast shows instead", async ({ page }) => {
    await atChapter(page, 4);
    await confirmChapter(page, 2); // the dialog handles both directions; this is a jump back
    await expect(page.locator('[data-testid="toast"][data-kind="backward"]')).toContainText("sealed again");
    await noRevealUiAppeared(page);
  });

  test("reload at chapter 3 fires nothing (not a forward commit)", async ({ page }) => {
    await atChapter(page, 3);
    await noRevealUiAppeared(page);
  });

  test("a failed forward fetch fires no reveal", async ({ page }) => {
    await atChapter(page, 1);
    await page.route(GRAPH_RE, async (route: Route) => {
      if (nOf(route.request().url()) === 2) await route.fulfill({ status: 500, body: "boom" });
      else await route.continue();
    });
    await confirmChapter(page, 2);
    await expect(page.locator('[data-testid="error-banner"]')).toBeVisible();
    await noRevealUiAppeared(page);
  });

  test("replay: the Dossier's replay button reopens the overlay from cache — zero network requests, and normal vs. deepening depends only on what's cached", async ({ page }) => {
    // Wren's ch.2 identity block (e12, SECRET_IDENTITY): the chapter-1 payload is already
    // cached (fetched as F8's n−1), and it has no identity edge for the pair -> NORMAL.
    await atChapter(page, 2);
    await page.waitForTimeout(400); // let the n−1 (=1) prefetch land
    let log = recordGraphRequests(page);
    await page.locator('[data-testid="identity-replay"]').first().click();
    await expect(overlay(page)).toBeVisible();
    await expect(overlay(page)).toHaveAttribute("data-kind", "normal");
    expect(log.urls).toEqual([]);
    await page.keyboard.press("Escape");

    // Wren's ch.4 identity block (e14, TRANSMIGRATED_INTO): the chapter-3 payload is
    // cached (F8's n−1 for bookmark=4), and it has e12/SECRET_IDENTITY for the same pair
    // -> DEEPENING, all from cache.
    await atChapter(page, 4);
    await page.waitForTimeout(400);
    log = recordGraphRequests(page);
    await page.locator('[data-testid="identity-replay"]').first().click();
    await expect(overlay(page)).toBeVisible();
    await expect(overlay(page)).toHaveAttribute("data-kind", "deepen");
    await expect(page.locator('[data-testid="reveal-before"]')).toBeVisible();
    expect(log.urls).toEqual([]);
  });

  test("quiet mode: persists across reload, and shows a toast instead of the overlay", async ({ page }) => {
    await page.evaluate((k) => localStorage.setItem(k, "1"), QUIET_KEY);
    await atChapter(page, 1);
    await page.reload();
    await page.waitForSelector('[data-testid="chapter-row-bookmark"][data-chapter="1"]');
    expect(await page.evaluate((k) => localStorage.getItem(k), QUIET_KEY)).toBe("1"); // survived the reload
    await confirmChapter(page, 2);
    await expect(quietToast(page)).toBeVisible();
    expect(await overlay(page).count()).toBe(0);
    await expect(quietToast(page)).toContainText(labelOf(2, "1"));
    // "Show reveals" turns quiet mode back off.
    await page.click('[data-testid="reveal-toast-show-again"]');
    expect(await page.evaluate((k) => localStorage.getItem(k), QUIET_KEY)).toBeNull();
  });

  test("quiet mode: a deepening reveal's toast uses the deepen kicker, and 'Read the evidence' opens the overlay with zero network requests", async ({ page }) => {
    await page.evaluate((k) => localStorage.setItem(k, "1"), QUIET_KEY);
    await atChapter(page, 3);
    const log = recordGraphRequests(page);
    await confirmChapter(page, 4);
    await expect(quietToast(page)).toBeVisible();
    await expect(quietToast(page)).toHaveAttribute("data-kind", "deepen");
    await expect(quietToast(page)).toContainText("the truth deepens");
    const before = log.urls.length;
    await page.click('[data-testid="reveal-toast-evidence"]');
    await expect(overlay(page)).toBeVisible();
    await expect(overlay(page)).toHaveAttribute("data-kind", "deepen");
    expect(log.urls.length).toBe(before); // opening from the toast is also cache-only
  });
});

test.describe("Reveal moment — synthetic-100 (test-only fixture via interception)", () => {
  const synthetic = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "synthetic-100.json"), "utf8")) as {
    elements: { nodes: { data: { revealed_chapter: number } }[]; edges: { data: { revealed_chapter: number; relation: string; evidence_span: string | null } }[] };
  };
  test.beforeEach(async ({ page }) => {
    await page.route(GRAPH_RE, async (route: Route) => {
      const n = nOf(route.request().url());
      const fenced = {
        slug: SLUG,
        n,
        elements: {
          nodes: synthetic.elements.nodes.filter((x) => x.data.revealed_chapter <= n),
          edges: synthetic.elements.edges.filter((x) => x.data.revealed_chapter <= n),
        },
      };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced) });
    });
    await fresh(page);
  });

  test("a jump producing >3 reveals shows the summary sheet, not sequential overlays", async ({ page }) => {
    // Fixture has 5 quoted identity edges (the 6th, quote-less, never reveals — P5/§8.4),
    // all new relative to chapter 1 -> a 1->4 jump surfaces exactly 5 reveals.
    await atChapter(page, 1);
    await confirmChapter(page, 4);
    await expect(summarySheet(page)).toBeVisible();
    expect(await overlay(page).count()).toBe(0);
    await expect(summarySheet(page).locator("h1")).toContainText("While you were reading: 5 identities revealed");
    expect(await page.locator('[data-testid="reveal-summary-row"]').count()).toBe(5);
    // expandable to the full quote
    const first = page.locator('[data-testid="reveal-summary-row"]').first();
    await first.locator("button").click();
    expect(await first.locator("blockquote").count()).toBe(1);
    await page.keyboard.press("Escape");
    await expect(summarySheet(page)).toHaveCount(0);
  });
});
