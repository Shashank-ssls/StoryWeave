// Chronicle (DESIGN_SPEC §6.4) end-to-end + its share of the fence: at every step of a
// bookmark walk the rendered rows/stitches/identity-links must equal an independent
// re-derivation from the R0 fixtures, and nothing above the bookmark may ever reach the
// DOM or a network request. Also covers F3 (constant sealed-band width) and the "Read on"
// button's dialog-only path.

import { test, expect, type Page, type Route } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { recordGraphRequests, assertNoGraphRequestAbove, dismissRevealIfShown, GRAPH_ROUTE_RE } from "./fenceHelpers";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const SLUG = "the-hollow-crown";
const KEY = `storyweave:bookmark:${SLUG}`;
const DRAWN = new Set(["Character", "Organization", "Place", "Item", "Ability"]);
const IDENTITY = new Set(["SAME_AS", "ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"]);

interface Node { id: string; label: string; type: string; first_seen_chapter: number; revealed_chapter: number }
interface Edge { id: string; source: string; target: string; relation: string; revealed_chapter: number; evidence_span: string | null }
interface Payload { elements: { nodes: { data: Node }[]; edges: { data: Edge }[] } }

const fixture = (n: number): Payload =>
  JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "hollow-crown", `graph-n${n}.json`), "utf8")) as Payload;

/** Independent re-derivation of the Chronicle's Principal-cast rows/stitches/identity
 *  links at chapter n, mirroring viewModel's merge rule and stemmaModel's principal rule
 *  (degree >= 2 OR any identity edge) without importing either. */
function expected(n: number) {
  const p = fixture(n);
  const nodes = new Map(p.elements.nodes.map((x) => [x.data.id, x.data]));
  const drawn = new Set([...nodes.values()].filter((x) => DRAWN.has(x.type)).map((x) => x.id));
  const rawEdges = p.elements.edges.map((e) => e.data).filter((e) => drawn.has(e.source) && drawn.has(e.target));
  const pairs = new Map<string, Edge>();
  for (const e of rawEdges) {
    const k = [e.source, e.target].sort().join("|");
    const cur = pairs.get(k);
    if (!cur || (IDENTITY.has(e.relation) && !IDENTITY.has(cur.relation))) pairs.set(k, e);
  }
  const merged = [...pairs.values()];
  const degree = new Map<string, number>();
  for (const e of merged) { degree.set(e.source, (degree.get(e.source) ?? 0) + 1); degree.set(e.target, (degree.get(e.target) ?? 0) + 1); }
  const idEndpoints = new Set(merged.filter((e) => IDENTITY.has(e.relation)).flatMap((e) => [e.source, e.target]));
  const principal = new Set([...drawn].filter((id) => (degree.get(id) ?? 0) >= 2 || idEndpoints.has(id)));
  const stitches = merged.filter((e) => !IDENTITY.has(e.relation) && principal.has(e.source) && principal.has(e.target)).map((e) => e.id).sort();
  return { rows: [...principal].sort(), identityLinks: identityTimelineExpected(n), stitches };
}

/** Independent re-derivation of the FULL identity timeline through chapter n (the
 *  Chronicle shows every past reveal, not just the current chapter's final state for a
 *  pair — e.g. Wren/Caelum's chapter-2 SECRET_IDENTITY `e12` is superseded by chapter-4's
 *  TRANSMIGRATED_INTO `e14` in the n=4 payload alone, but the Chronicle must still show
 *  BOTH as separate markers). Walks every chapter 1..n, pushing an edge id whenever its
 *  pair's relation is new or has changed since the last chapter that carried it.
 */
function identityTimelineExpected(n: number): string[] {
  const seen = new Map<string, string>();
  const ids: string[] = [];
  for (let k = 1; k <= n; k++) {
    const p = fixture(k);
    const nodes = new Map(p.elements.nodes.map((x) => [x.data.id, x.data]));
    const drawn = new Set([...nodes.values()].filter((x) => DRAWN.has(x.type)).map((x) => x.id));
    const idEdges = p.elements.edges
      .map((e) => e.data)
      .filter((e) => IDENTITY.has(e.relation) && drawn.has(e.source) && drawn.has(e.target) && e.evidence_span);
    for (const e of idEdges) {
      const key = [e.source, e.target].sort().join("|");
      if (seen.get(key) !== e.relation) {
        ids.push(e.id);
        seen.set(key, e.relation);
      }
    }
  }
  return ids.sort();
}

async function attachLog(log: ReturnType<typeof recordGraphRequests>): Promise<void> {
  await test.info().attach("graph-requests", { body: JSON.stringify(log.urls, null, 2), contentType: "application/json" });
}
async function openAt(page: Page, n: number): Promise<void> {
  await page.goto(`/#/work/${SLUG}/chronicle`);
  await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)] as const);
  await page.reload();
  await page.waitForSelector('[data-testid="chronicle-svg"]');
  await page.waitForTimeout(300);
}
async function confirmChapter(page: Page, from: number, n: number): Promise<void> {
  await dismissRevealIfShown(page); // a prior forward step's reveal overlay would block this click
  if (n < from) {
    // "Read on" only offers forward (and is absent at the last chapter) — backward moves
    // go through the global `[` shortcut instead, same as every other screen (§8.5).
    for (let i = 0; i < from - n; i++) await page.keyboard.press("[");
  } else {
    await page.click('[data-testid="chronicle-read-on"]');
    await page.waitForSelector('[data-testid="chapter-dialog"]');
    await page.fill('[data-testid="chapter-input"]', String(n));
    await page.click('[data-testid="set-bookmark"]');
  }
  await page.waitForTimeout(300);
  await dismissRevealIfShown(page);
}
async function domState(page: Page) {
  return page.evaluate(() => ({
    rows: Array.from(document.querySelectorAll('[data-testid="chronicle-row"]')).map((el) => el.getAttribute("data-entity") ?? "").sort(),
    identityLinks: Array.from(document.querySelectorAll('[data-testid="chronicle-identity-link"]')).map((el) => el.getAttribute("data-edge") ?? "").sort(),
    stitches: Array.from(document.querySelectorAll('[data-testid="chronicle-stitch"]')).map((el) => el.getAttribute("data-edge") ?? "").sort(),
    text: document.body.innerText,
  }));
}

test.describe("Chronicle (§6.4) — fenced content at every step", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#/");
    await page.evaluate((k) => localStorage.removeItem(k), KEY);
  });

  test("walk 1->2->3->4->2: rows/stitches/identity-links == fixture at each step; nothing above the bookmark; only n and n-1 ever requested", async ({ page }) => {
    const log = recordGraphRequests(page);
    await openAt(page, 1);
    const walk = [1, 2, 3, 4, 2];
    for (let step = 0; step < walk.length; step++) {
      const n = walk[step]!;
      const before = log.urls.length;
      if (step > 0) await confirmChapter(page, walk[step - 1]!, n);
      await page.waitForTimeout(500); // history backfill + n-1 fetch settle
      const exp = expected(n);
      const got = await domState(page);
      expect(got.rows, `rows @${n}`).toEqual(exp.rows);
      expect(got.identityLinks, `identity links @${n}`).toEqual(exp.identityLinks);
      expect(got.stitches, `stitches @${n}`).toEqual(exp.stitches);
      // F2: never a hint of what's beyond — the demo's later-chapter-only names never appear
      if (n < 3) expect(got.text).not.toContain("Lady Veris");
      if (n < 2) expect(got.text).not.toContain("Prince Caelum");
      assertNoGraphRequestAbove({ urls: log.urls.slice(before), stop: () => {} }, n);
    }
    const ns = log.urls.map((u) => Number(/n=(\d+)/.exec(u)?.[1]));
    expect(ns.every((k) => [1, 2, 3, 4].includes(k)), `unexpected chapters requested: ${ns}`).toBe(true);
    await attachLog(log);
  });

  test("the deepening pair (Wren/Caelum) shows both its first reveal (ch.2, secret identity) and its deepening marker (ch.4, transmigration)", async ({ page }) => {
    await openAt(page, 4);
    await page.waitForTimeout(600); // ensureHistory backfill (1..4) must complete
    const links = page.locator('[data-testid="chronicle-identity-link"]');
    await expect(links).toHaveCount(3);
    await expect(page.locator('[data-testid="chronicle-identity-link"][data-edge="e12"]')).toHaveAttribute("data-kind", "normal");
    await expect(page.locator('[data-testid="chronicle-identity-link"][data-edge="e14"]')).toHaveAttribute("data-kind", "deepen");
    await expect(page.locator('[data-testid="chronicle-identity-link"][data-edge="e13"]')).toHaveAttribute("data-kind", "normal");
    // default selection is the most recent (e14) with the "Before" explanation line
    await expect(page.locator('[data-testid="chronicle-reveal-explain"]')).toContainText("Chapter II");
  });

  test("F3 — the sealed band is exactly one column-width, constant regardless of the bookmark or remaining chapters", async ({ page }) => {
    await openAt(page, 1);
    const w1 = await page.locator('[data-testid="chronicle-sealed"]').getAttribute("data-width");
    await openAt(page, 4);
    const w4 = await page.locator('[data-testid="chronicle-sealed"]').getAttribute("data-width");
    expect(w1).toBe(w4); // same layout mode (small, bookmark <= 12) -> same constant width
  });

  test('"Read on" opens the R3 confirm dialog prefilled with bookmark+1 — never a direct fetch', async ({ page }) => {
    await openAt(page, 3);
    const log = recordGraphRequests(page);
    await page.click('[data-testid="chronicle-read-on"]');
    await expect(page.locator('[data-testid="chapter-dialog"]')).toBeVisible();
    expect(await page.locator('[data-testid="chapter-input"]').inputValue()).toBe("4");
    expect(log.urls, "opening the dialog must not fetch anything").toEqual([]);
    await page.click('[data-testid="set-bookmark"]');
    await expect(page.locator('[data-testid="chapter-row-bookmark"], [data-testid="chronicle-svg"]')).toBeVisible();
    expect(log.urls.length, "confirming does fetch, exactly once for the new chapter").toBeGreaterThan(0);
    assertNoGraphRequestAbove(log, 4);
  });

  test('"Read on" is absent at the last chapter', async ({ page }) => {
    await openAt(page, 4);
    await expect(page.locator('[data-testid="chronicle-read-on"]')).toHaveCount(0);
  });
});

test.describe("Chronicle — large-N layout (synthetic, via route interception)", () => {
  const nodes = Array.from({ length: 10 }, (_, i) => {
    const chapter = 1 + i * 4;
    return { data: { id: String(i + 1), label: `Character ${i + 1}`, type: "Character", subtype: "Person", importance: 0.5, first_seen_chapter: chapter, revealed_chapter: chapter, extraction_method: "gliner", evidence_span: "x", properties: {} } };
  });
  const edges = [
    { data: { id: "se1", source: "1", target: "2", relation: "Ally", tier: 2, first_seen_chapter: 5, revealed_chapter: 5, extraction_method: "rule", evidence_span: "x" } },
    { data: { id: "se2", source: "3", target: "4", relation: "SECRET_IDENTITY", tier: 3, first_seen_chapter: 30, revealed_chapter: 30, extraction_method: "llm", evidence_span: "the two were one" } },
  ];

  async function largeBookAt(page: Page, bookmark: number): Promise<void> {
    await page.route(/\/api\/v1\/works$/, async (route: Route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ works: [{ id: 1, slug: SLUG, title: "The Hollow Crown", chapter_count: 100 }] }) });
    });
    await page.route(GRAPH_ROUTE_RE, async (route: Route) => {
      const n = Number(/[?&]n=(\d+)/.exec(route.request().url())?.[1]);
      const fenced = { slug: SLUG, n, elements: { nodes: nodes.filter((x) => x.data.revealed_chapter <= n), edges: edges.filter((x) => x.data.revealed_chapter <= n) } };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced) });
    });
    await page.goto(`/#/work/${SLUG}/chronicle`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(bookmark)] as const);
    await page.reload();
    await page.waitForSelector('[data-testid="chronicle-svg"]');
    await page.waitForTimeout(500);
  }

  test("F3 across modes: the small-mode and large-mode sealed widths are each their own constant, and differ from each other", async ({ page }) => {
    await largeBookAt(page, 40);
    const w40 = await page.locator('[data-testid="chronicle-sealed"]').getAttribute("data-width");
    await largeBookAt(page, 90);
    const w90 = await page.locator('[data-testid="chronicle-sealed"]').getAttribute("data-width");
    expect(w40).toBe(w90); // both > 12 -> same large-mode column width, regardless of remaining chapters
  });

  test("no page-level horizontal scroll at 1280x720 — only the chart's own scroll area may scroll", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await largeBookAt(page, 90);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1); // sub-pixel rounding only
  });
});

test.describe("Chronicle — synthetic-100 (cast overflow at small-N)", () => {
  const synthetic = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "synthetic-100.json"), "utf8")) as Payload;
  const fenced = (n: number) => ({
    slug: SLUG, n,
    elements: {
      nodes: synthetic.elements.nodes.filter((x) => x.data.revealed_chapter <= n),
      edges: synthetic.elements.edges.filter((x) => x.data.revealed_chapter <= n),
    },
  });

  test.beforeEach(async ({ page }) => {
    await page.route(GRAPH_ROUTE_RE, async (route: Route) => {
      const n = Number(/[?&]n=(\d+)/.exec(route.request().url())?.[1]);
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced(n)) });
    });
  });

  test("no page-level horizontal scroll at 1280x720 with a large principal cast", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(`/#/work/${SLUG}/chronicle`);
    await page.evaluate((k) => localStorage.setItem(k, "4"), KEY);
    await page.reload();
    await page.waitForSelector('[data-testid="chronicle-svg"]');
    await page.waitForTimeout(500);
    expect(await page.locator('[data-testid="chronicle-row"]').count()).toBeGreaterThan(10);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
