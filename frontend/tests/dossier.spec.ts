// Dossier (DESIGN_SPEC §6.2) end-to-end + its share of the fence: at every step of a
// bookmark walk the rendered DOM must contain exactly the entities/edges of the fenced
// payload for that chapter (compared to the R0 fixtures, which are real captured
// responses) and nothing else. Also activates F4 (dossier variant) and F8, and closes the
// R3 follow-up (backward-fetch failure → §6.7 error card).

import { test, expect, type Page, type Route } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
import { recordGraphRequests, assertNoGraphRequestAbove, GRAPH_ROUTE_RE, type GraphRequestLog } from "./fenceHelpers";

const SLUG = "the-hollow-crown";
const KEY = `storyweave:bookmark:${SLUG}`;
const DRAWN = new Set(["Character", "Organization", "Place", "Item", "Ability"]);
const IDENTITY = new Set(["SAME_AS", "ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"]);

interface Node { id: string; label: string; type: string; first_seen_chapter: number; revealed_chapter: number }
interface Edge { id: string; source: string; target: string; relation: string; revealed_chapter: number; evidence_span: string | null }
interface Payload { elements: { nodes: { data: Node }[]; edges: { data: Edge }[] } }

const fixture = (n: number): Payload =>
  JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "hollow-crown", `graph-n${n}.json`), "utf8")) as Payload;

/** Independent re-derivation of what the dossier may show for `entity` at chapter n. */
function expected(n: number, entity: string) {
  const p = fixture(n);
  const nodes = new Map(p.elements.nodes.map((x) => [x.data.id, x.data]));
  const drawn = new Set([...nodes.values()].filter((x) => DRAWN.has(x.type)).map((x) => x.id));
  const edges = p.elements.edges.map((e) => e.data).filter((e) => drawn.has(e.source) && drawn.has(e.target));
  // merge parallels: identity absorbs
  const pairs = new Map<string, Edge>();
  for (const e of edges) {
    const k = [e.source, e.target].sort().join("|");
    const cur = pairs.get(k);
    if (!cur || (IDENTITY.has(e.relation) && !IDENTITY.has(cur.relation))) pairs.set(k, e);
  }
  const merged = [...pairs.values()];
  const touching = merged.filter((e) => e.source === entity || e.target === entity);
  const identityIds = touching.filter((e) => IDENTITY.has(e.relation)).map((e) => e.id).sort();
  const tieOthers = touching.filter((e) => !IDENTITY.has(e.relation)).map((e) => (e.source === entity ? e.target : e.source)).sort();
  const people = [...nodes.values()].filter((x) => x.type === "Character").map((x) => x.id).sort();
  const adj = new Map<string, Set<string>>();
  for (const e of merged) {
    (adj.get(e.source) ?? adj.set(e.source, new Set()).get(e.source)!).add(e.target);
    (adj.get(e.target) ?? adj.set(e.target, new Set()).get(e.target)!).add(e.source);
  }
  const ego = new Set([entity]);
  for (const a of adj.get(entity) ?? []) { ego.add(a); for (const b of adj.get(a) ?? []) ego.add(b); }
  const egoEdges = merged.filter((e) => ego.has(e.source) && ego.has(e.target)).map((e) => e.id).sort();
  return { identityIds, tieOthers, people, egoNodes: [...ego].sort(), egoEdges, present: drawn.has(entity) };
}

/** "changed" per F8: new at n vs n−1, or endpoint of an identity edge revealed at exactly n. */
function expectedChanged(n: number): string[] {
  if (n <= 1) return [];
  const prev = new Set(fixture(n - 1).elements.nodes.map((x) => x.data.id));
  const cur = fixture(n);
  const out = new Set<string>();
  for (const x of cur.elements.nodes) if (x.data.type === "Character" && !prev.has(x.data.id)) out.add(x.data.id);
  for (const e of cur.elements.edges) if (IDENTITY.has(e.data.relation) && e.data.revealed_chapter === n) { out.add(e.data.source); out.add(e.data.target); }
  return [...out].sort();
}

async function attachLog(log: GraphRequestLog): Promise<void> {
  await test.info().attach("graph-requests", { body: JSON.stringify(log.urls, null, 2), contentType: "application/json" });
}
async function openAt(page: Page, n: number, entity = "1"): Promise<void> {
  await page.goto(`/#/work/${SLUG}/entity/${entity}`);
  await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)] as const);
  await page.reload();
  await page.waitForSelector(`[data-testid="chapter-row-bookmark"][data-chapter="${n}"]`);
}
async function confirmChapter(page: Page, n: number): Promise<void> {
  await page.click('[data-testid="change-chapter"]');
  await page.fill('[data-testid="chapter-input"]', String(n));
  await page.click('[data-testid="set-bookmark"]');
  await expect(page.locator('[data-testid="chapter-row-bookmark"]')).toHaveAttribute("data-chapter", String(n));
}
async function domState(page: Page) {
  await page.waitForSelector('[data-testid="entity-main"], [data-testid="state-not-present"]');
  return page.evaluate(() => {
    const attrs = (sel: string, a: string) => Array.from(document.querySelectorAll(sel)).map((el) => el.getAttribute(a) ?? "").sort();
    const ego = document.querySelector('[data-testid="ego-graph"]') as HTMLElement | null;
    return {
      identityIds: attrs('[data-testid="identity-block"]', "data-edge"),
      tieOthers: attrs('[data-testid="tie"]', "data-entity"),
      people: attrs('[data-testid="cast-row"]', "data-entity"),
      changed: Array.from(document.querySelectorAll('[data-testid="cast-row"]')).filter((r) => r.querySelector('[data-testid="changed-tag"]')).map((r) => r.getAttribute("data-entity") ?? "").sort(),
      egoNodes: (ego?.dataset.nodes ?? "").split(",").filter(Boolean).sort(),
      egoEdges: (ego?.dataset.edges ?? "").split(",").filter(Boolean).sort(),
      present: !!document.querySelector('[data-testid="entity-main"]'),
      mainText: (document.querySelector("main")?.textContent ?? ""),
    };
  });
}

test.describe("Dossier (§6.2) — fenced content at every step", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#/");
    await page.evaluate((k) => localStorage.removeItem(k), KEY);
  });

  test("walk 1→2→3→4→2: DOM == fixture for Wren at each step; F8 requests only n and n−1", async ({ page }) => {
    const log = recordGraphRequests(page);
    await openAt(page, 1);
    let step = 0;
    for (const n of [1, 2, 3, 4, 2]) {
      const before = log.urls.length;
      if (step++ > 0) await confirmChapter(page, n);
      // the ego graph re-renders on data change; wait for the n−1 payload (changed tags) to settle
      await page.waitForTimeout(400);
      const exp = expected(n, "1");
      const got = await domState(page);
      expect(got.present, `chapter ${n}`).toBe(true);
      expect(got.identityIds, `identity blocks @${n}`).toEqual(exp.identityIds);
      expect(got.tieOthers, `ties @${n}`).toEqual(exp.tieOthers);
      expect(got.people, `cast @${n}`).toEqual(exp.people);
      expect(got.egoNodes, `ego nodes @${n}`).toEqual(exp.egoNodes);
      expect(got.egoEdges, `ego edges @${n}`).toEqual(exp.egoEdges);
      expect(got.changed, `changed tags @${n}`).toEqual(expectedChanged(n));
      // Lady Veris (12) / the Gray Sparrow (11) exist only from chapter 3
      expect(got.mainText.includes("Lady Veris") || got.people.includes("12")).toBe(n >= 3);
      // F1 per step: nothing requested during this step exceeds this step's bookmark.
      assertNoGraphRequestAbove({ urls: log.urls.slice(before), stop: () => {} }, n);
    }
    // F8: every request was for a bookmark or its predecessor, never anything else.
    const ns = log.urls.map((u) => Number(/n=(\d+)/.exec(u)?.[1]));
    expect(ns.every((k) => [1, 2, 3, 4].includes(k))).toBe(true);
    await attachLog(log);
  });

  test("Veris–Sparrow ALIAS block exists at 3, and Veris is absent (§6.7 card, F4 copy) at 2", async ({ page }) => {
    await openAt(page, 3, "12");
    const at3 = await domState(page);
    expect(at3.present).toBe(true);
    expect(at3.identityIds).toEqual(expected(3, "12").identityIds);
    expect(at3.identityIds.length).toBe(1);
    await expect(page.locator('[data-testid="identity-block"]')).toHaveAttribute("data-relation", "ALIAS");
    await expect(page.locator('[data-testid="identity-quote"]')).toContainText("the Sparrow and Veris were one");

    await page.keyboard.press("["); // → 2: Veris was never met
    await expect(page.locator('[data-testid="state-not-present"]')).toBeVisible();
    const card = await page.locator('[data-testid="state-not-present"]').innerText();
    expect(card).toContain("No one by that name, as of Chapter II.");
    // F4: the spec copy deliberately says "we won't say whether they ever appear" —
    // what it must never say is that they DO appear later.
    expect(card.toLowerCase()).not.toMatch(/appears? later|later chapter|not yet|will appear/);
    expect(card).not.toContain("Veris"); // never names them
    const got = await domState(page);
    expect(got.present).toBe(false);
    expect(got.identityIds).toEqual([]);
    expect(got.egoNodes).toEqual([]); // no old data anywhere
    await page.click('[data-testid="go-principal"]');
    await expect(page.locator('[data-testid="entity-h1"]')).toHaveText("Wren");
  });

  test("`#/work/:slug` lands on the principal character (highest degree)", async ({ page }) => {
    await page.goto(`/#/work/${SLUG}`);
    await expect(page.locator('[data-testid="entity-h1"]')).toHaveText("Wren");
    expect(await page.evaluate(() => location.hash)).toBe(`#/work/${SLUG}/entity/1`);
  });

  test("R3 follow-up — backward fetch failure: bookmark commits, no higher data remains, §6.7 error card, Try again", async ({ page }) => {
    // Open at 4: the cache holds 4 and (for "changed" tags) 3 — never 1. Then fail n=1.
    await openAt(page, 4);
    await page.waitForSelector('[data-testid="entity-main"]');
    await page.waitForTimeout(500); // let the n−1 (=3) fetch land so it can't confuse the log
    let fail = true;
    await page.route(GRAPH_ROUTE_RE, async (route: Route) => {
      const n = Number(/n=(\d+)/.exec(route.request().url())?.[1]);
      if (fail && n === 1) await route.fulfill({ status: 500, body: "boom" });
      else await route.continue();
    });
    const log = recordGraphRequests(page);
    await page.click('[data-testid="change-chapter"]');
    await page.fill('[data-testid="chapter-input"]', "1");
    await page.click('[data-testid="set-bookmark"]');
    await expect(page.locator('[data-testid="chapter-row-bookmark"]')).toHaveAttribute("data-chapter", "1");
    const card = page.locator('[data-testid="state-error"]');
    await expect(card).toBeVisible();
    await expect(card).toContainText("The archive didn't answer.");
    expect(await page.evaluate((k) => localStorage.getItem(k), KEY)).toBe("1");
    const got = await page.evaluate(() => ({
      main: !!document.querySelector('[data-testid="entity-main"]'),
      cast: document.querySelectorAll('[data-testid="cast-row"]').length,
      ego: !!document.querySelector('[data-testid="ego-graph"]'),
      text: document.body.innerText,
    }));
    expect(got.main).toBe(false);
    expect(got.cast).toBe(0);
    expect(got.ego).toBe(false);
    expect(got.text).not.toContain("Prince Caelum"); // chapter-4 data gone from the DOM
    // Try again re-requests exactly n=1, then the dossier renders at chapter 1
    fail = false;
    await page.click('[data-testid="state-retry"]');
    await expect(page.locator('[data-testid="entity-h1"]')).toHaveText("Wren");
    expect(log.urls.map((u) => Number(/n=(\d+)/.exec(u)?.[1]))).toEqual([1, 1]);
    assertNoGraphRequestAbove(log, 1);
    await attachLog(log);
  });

  test("loading skeleton shows before data, no spinner", async ({ page }) => {
    await page.route(GRAPH_ROUTE_RE, async (route: Route) => {
      await new Promise((r) => setTimeout(r, 1200));
      await route.continue();
    });
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await expect(page.locator('[data-testid="skeleton"]')).toBeVisible();
    expect(await page.locator('[data-testid="skeleton"] > div').count()).toBe(4); // H1 bar + 3
    await expect(page.locator('[data-testid="entity-h1"]')).toHaveText("Wren", { timeout: 10_000 });
  });
});

test.describe("Dossier — synthetic-100 (test-only fixture via interception)", () => {
  const synthetic = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "synthetic-100.json"), "utf8")) as Payload;
  // A fake server fence: only rows revealed at or before n leave the "server".
  const fenced = (n: number) => ({
    slug: SLUG,
    n,
    elements: {
      nodes: synthetic.elements.nodes.filter((x) => x.data.revealed_chapter <= n),
      edges: synthetic.elements.edges.filter((x) => x.data.revealed_chapter <= n),
    },
  });

  test.beforeEach(async ({ page }) => {
    await page.route(GRAPH_ROUTE_RE, async (route: Route) => {
      const n = Number(/n=(\d+)/.exec(route.request().url())?.[1]);
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fenced(n)) });
    });
    await page.goto("/#/");
    await page.evaluate((k) => localStorage.setItem(k, "4"), KEY);
  });

  test("cast overflow: top 12, 'All 70 people →', searchable full list; ties overflow at 12", async ({ page }) => {
    const warnings: string[] = [];
    page.on("console", (m) => { if (m.type() === "warning") warnings.push(m.text()); });
    await page.goto(`/#/work/${SLUG}`);
    await expect(page.locator('[data-testid="entity-h1"]')).toHaveText("Ael of the Marsh");
    expect(await page.locator('[data-testid="cast-row"]').count()).toBe(12);
    await expect(page.locator('[data-testid="cast-all"]')).toHaveText("All 70 people →");
    await page.click('[data-testid="cast-all"]');
    expect(await page.locator('[data-testid="cast-row"]').count()).toBe(70);
    await page.fill('[data-testid="cast-search"]', "kestrel");
    expect(await page.locator('[data-testid="cast-row"]').count()).toBeGreaterThan(0);
    expect(await page.locator('[data-testid="cast-row"]').count()).toBeLessThan(10);
    // ties: hub has 20 social ties + 1 MemberOf (+1 ALIAS, shown as an identity block, not a tie)
    expect(await page.locator('[data-testid="tie"]').count()).toBe(12);
    await expect(page.locator('[data-testid="ties-all"]')).toHaveText("All 21 ties →");
    await page.click('[data-testid="ties-all"]');
    expect(await page.locator('[data-testid="tie"]').count()).toBe(21);
    expect(await page.locator('[data-testid="identity-block"]').count()).toBe(1);
    // the one quote-less identity edge was dropped with exactly one console.warn (§8.4)
    const drops = warnings.filter((w) => w.includes("no evidence_span"));
    expect(drops.length).toBeGreaterThanOrEqual(1);
    expect(new Set(drops).size).toBe(1);
    // ego graph rendered something legible-sized (nodes mirrored to the DOM)
    const ego = await page.locator('[data-testid="ego-graph"]').getAttribute("data-nodes");
    expect((ego ?? "").split(",").length).toBeGreaterThan(10);
  });
});
