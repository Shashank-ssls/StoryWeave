// The Stemma (DESIGN_SPEC §6.3, §7, §8.3) end-to-end + its share of the fence. The canvas
// is read through the dev-only `window.__storyweaveCy.stemma` handle (never UI-visible).

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
const MEMBERSHIP = new Set(["MemberOf", "AffiliatedWith", "LeaderOf"]);

interface Node { id: string; label: string; type: string; revealed_chapter: number }
interface Edge { id: string; source: string; target: string; relation: string; revealed_chapter: number; evidence_span: string | null }
interface Payload { elements: { nodes: { data: Node }[]; edges: { data: Edge }[] } }
const fixture = (n: number): Payload => JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "hollow-crown", `graph-n${n}.json`), "utf8")) as Payload;
const synthetic = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "synthetic-100.json"), "utf8")) as Payload;

/** Independent re-derivation of the view model's drawn nodes / merged edges. */
function drawn(p: Payload) {
  const nodes = new Map(p.elements.nodes.map((x) => [x.data.id, x.data]));
  const ids = new Set([...nodes.values()].filter((x) => DRAWN.has(x.type)).map((x) => x.id));
  const pairs = new Map<string, Edge>();
  for (const { data: e } of p.elements.edges) {
    if (!ids.has(e.source) || !ids.has(e.target)) continue;
    if (IDENTITY.has(e.relation) && !(e.evidence_span ?? "").trim()) continue;
    const k = [e.source, e.target].sort().join("|");
    const cur = pairs.get(k);
    if (!cur || (IDENTITY.has(e.relation) && !IDENTITY.has(cur.relation))) pairs.set(k, e);
  }
  const edges = [...pairs.values()];
  const degree = new Map<string, number>();
  for (const e of edges) { degree.set(e.source, (degree.get(e.source) ?? 0) + 1); degree.set(e.target, (degree.get(e.target) ?? 0) + 1); }
  const idEnds = new Set(edges.filter((e) => IDENTITY.has(e.relation)).flatMap((e) => [e.source, e.target]));
  return { nodes, ids: [...ids].sort(), edges, edgeIds: edges.map((e) => e.id).sort(), degree, idEnds };
}

async function cyState(page: Page) {
  return page.evaluate(() => {
    const cy = (window as unknown as { __storyweaveCy?: { stemma: unknown } }).__storyweaveCy?.stemma as {
      nodes(): { map<T>(f: (n: { id(): string; data(k: string): unknown; hasClass(c: string): boolean }) => T): T[] };
      edges(): { map<T>(f: (e: { id(): string }) => T): T[] };
      zoom(): number;
    } | null;
    if (!cy) return null;
    return {
      nodes: cy.nodes().map((n) => n.id()).sort(),
      edges: cy.edges().map((e) => e.id()).sort(),
      displays: Object.fromEntries(cy.nodes().map((n) => [n.id(), n.data("display") as string])),
      focus: cy.nodes().map((n) => (n.hasClass("focus") ? n.id() : null)).filter(Boolean),
      zoom: cy.zoom(),
    };
  });
}

async function openStemma(page: Page, n: number, focus?: string): Promise<void> {
  await page.goto(`/#/work/${SLUG}/web${focus ? `?focus=${focus}` : ""}`);
  await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, String(n)] as const);
  await page.reload();
  await page.waitForSelector(`[data-testid="chapter-row-bookmark"][data-chapter="${n}"], [data-testid="stemma-footer"]`);
  await page.waitForFunction(() => !!(window as unknown as { __storyweaveCy?: { stemma: unknown } }).__storyweaveCy?.stemma);
  await page.waitForTimeout(900); // first fit
}

async function setBookmark(page: Page, n: number): Promise<void> {
  await page.click('[data-testid="stemma-change"]');
  await page.fill('[data-testid="chapter-input"]', String(n));
  await page.click('[data-testid="set-bookmark"]');
  await expect(page.locator('[data-testid="stemma-footer"]')).toContainText(`Read to Chapter ${["", "I", "II", "III", "IV"][n]} of 4`);
  await page.waitForTimeout(700);
  // R6: see the matching comment in dossier.spec.ts's confirmChapter — a real forward move
  // here would otherwise leave the reveal overlay's backdrop blocking the next click.
  await dismissRevealIfShown(page);
}

test.describe("Stemma — fenced canvas at every step", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#/");
    await page.evaluate((k) => localStorage.removeItem(k), KEY);
  });

  test("walk 1→2→3→4→2: cy ids == view model of the fenced payload (Everyone), principal ⊆ that; no request above", async ({ page }) => {
    const log = recordGraphRequests(page);
    await openStemma(page, 1);
    await page.click('[data-testid="cast-everyone"]');
    let step = 0;
    for (const n of [1, 2, 3, 4, 2]) {
      const before = log.urls.length;
      if (step++ > 0) await setBookmark(page, n);
      const exp = drawn(fixture(n));
      const got = await cyState(page);
      expect(got, `cy @${n}`).not.toBeNull();
      expect(got!.nodes, `nodes @${n}`).toEqual(exp.ids);
      expect(got!.edges, `edges @${n}`).toEqual(exp.edgeIds);
      // Veris–Sparrow ALIAS (e13) only from chapter 3; nothing about them anywhere before.
      expect(got!.edges.includes("e13")).toBe(n >= 3);
      if (n < 3) expect(await page.locator("body").innerText()).not.toMatch(/Veris|Sparrow/);
      assertNoGraphRequestAbove({ urls: log.urls.slice(before), stop: () => {} }, n);
    }
    // Principal view is a subset of the same fenced set
    await page.click('[data-testid="cast-principal"]');
    await page.waitForTimeout(300);
    const p = await cyState(page);
    const all = new Set(drawn(fixture(2)).ids);
    for (const id of p!.nodes) expect(all.has(id)).toBe(true);
    await test.info().attach("graph-requests", { body: JSON.stringify(log.urls, null, 2), contentType: "application/json" });
  });

  test("F4 (Stemma) — searching a later-chapter name at an earlier bookmark: neutral no-match, nothing leaks", async ({ page }) => {
    await openStemma(page, 2);
    await page.fill('[data-testid="stemma-search"]', "Veris");
    await expect(page.locator('[data-testid="search-no-match"]')).toBeVisible();
    const text = await page.locator('[data-testid="search-no-match"]').innerText();
    expect(text).toContain("No one by that name, as of Chapter II.");
    expect(text).toContain("We won't say whether they ever appear. Even that would be a spoiler.");
    expect(await page.locator('[data-testid="search-results"]').count()).toBe(0);
    // and at chapter 3 the same query resolves and focuses her
    await setBookmark(page, 3);
    await page.fill('[data-testid="stemma-search"]', "Veris");
    await expect(page.locator('[data-testid="search-results"]')).toContainText("Lady Veris");
    await page.keyboard.press("Enter");
    await expect(page.locator('[data-testid="focus-label"]')).toContainText("Focused on Lady Veris");
    expect(await page.evaluate(() => location.hash)).toBe(`#/work/${SLUG}/web?focus=12`);
  });

  test("shared URL ?focus=<unrevealed id> at bookmark 1 falls back to the principal and leaks nothing", async ({ page }) => {
    const titleBefore = await page.title();
    await openStemma(page, 1, "12");
    expect(await page.evaluate(() => location.hash)).toBe(`#/work/${SLUG}/web?focus=1`);
    await expect(page.locator('[data-testid="focus-label"]')).toContainText("Focused on Wren");
    const got = await cyState(page);
    expect(got!.nodes).not.toContain("12");
    expect(got!.focus).toEqual(["1"]);
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/Veris/);
    expect(await page.locator('[data-testid="panel-node"]').getAttribute("data-entity")).toBe("1");
    expect(await page.title()).toBe(titleBefore);
  });

  test("bookmark moves back while focused on an entity that vanishes: quiet fallback to the principal", async ({ page }) => {
    await openStemma(page, 3, "12");
    await expect(page.locator('[data-testid="focus-label"]')).toContainText("Lady Veris");
    await page.keyboard.press("[");
    await expect(page.locator('[data-testid="focus-label"]')).toContainText("Focused on Wren");
    await page.waitForTimeout(500);
    expect(await page.locator("body").innerText()).not.toMatch(/Veris|Sparrow/);
    expect((await cyState(page))!.nodes).not.toContain("12");
    expect(await page.evaluate(() => location.hash)).toBe(`#/work/${SLUG}/web?focus=1`);
  });

  test("edge tooltip (identity: label + 80-char quote; social: label only) and the selection panel (full quote)", async ({ page }) => {
    await openStemma(page, 3);
    await page.click('[data-testid="cast-everyone"]');
    await page.waitForTimeout(300);
    const emit = (id: string, ev: string) => page.evaluate(([i, e]) => {
      const cy = (window as unknown as { __storyweaveCy: { stemma: { getElementById(id: string): { emit(e: string): void } } } }).__storyweaveCy.stemma;
      cy.getElementById(i).emit(e);
    }, [id, ev] as const);
    await emit("e12", "mouseover");
    const tip = page.locator('[data-testid="edge-tooltip"]');
    await expect(tip).toBeVisible();
    await expect(tip).toContainText("secret identity · Chapter II");
    await expect(tip).toContainText("Wren was Caelum.");
    await emit("e12", "mouseout");
    await expect(tip).toHaveCount(0);
    await emit("e1", "mouseover");
    await expect(tip).toContainText("in · Chapter I");
    expect(await tip.innerText()).not.toContain("“");
    await emit("e1", "mouseout");
    // click the identity edge → panel
    await emit("e13", "tap");
    const panel = page.locator('[data-testid="panel-edge"]');
    await expect(panel).toBeVisible();
    await expect(panel).toContainText("Selected link · Chapter III");
    await expect(panel).toContainText("the Gray Sparrow is Lady Veris");
    await expect(page.locator('[data-testid="panel-quote"]')).toHaveText("“the Sparrow and Veris were one”");
    await expect(panel).toContainText("Open the Gray Sparrow's dossier");
    await expect(page.locator('[data-testid="panel-legend"]')).toContainText("a revealed identity");
    // Esc clears the edge selection first
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="panel-edge"]')).toHaveCount(0);
  });

  test("keyboard: `/` → search; arrows cycle neighbours with the ring; Enter focuses; Esc clears focus", async ({ page }) => {
    await openStemma(page, 4);
    await page.keyboard.press("/");
    expect(await page.evaluate(() => document.activeElement?.getAttribute("data-testid"))).toBe("stemma-search");
    await page.keyboard.press("Escape"); // leaves the input
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.keyboard.press("ArrowRight");
    const ring = await page.evaluate(() => {
      const cy = (window as unknown as { __storyweaveCy: { stemma: { nodes(sel: string): { map<T>(f: (n: { id(): string }) => T): T[] } } } }).__storyweaveCy.stemma;
      return cy.nodes(".kbd-ring").map((n) => n.id());
    });
    expect(ring).toHaveLength(1);
    await page.keyboard.press("Enter");
    await expect(page.locator('[data-testid="focus-label"]')).not.toContainText("Focused on Wren");
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="focus-label"]')).toContainText("The whole web");
    await expect(page.locator('[data-testid="clear-focus"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="steps"]')).toHaveCount(0);
  });

  test("R9 §11 — screen-reader mirror of the focused neighbourhood updates on focus change and contains only fenced ties", async ({ page }) => {
    await openStemma(page, 1, "1");
    const mirror = page.locator('[data-testid="focus-mirror"]');
    await expect(mirror).toHaveAttribute("role", "status");
    await expect(mirror).toHaveText("Wren — ties: Aldercross (in, Chapter I), Glass-sight (has ability, Chapter I), the heron ring (owns, Chapter I)");
    // fenced: no later-chapter tie (Prince Caelum/transmigration) leaks at bookmark 1
    expect(await mirror.innerText()).not.toMatch(/Caelum|transmigration/);
    await page.click('[data-testid="clear-focus"]');
    await expect(mirror).toHaveText("Nothing focused. Choose a name from the rail, or press / to search.");
    // re-focus at chapter 4: the mirror now includes the identity tie, by chapter
    await setBookmark(page, 4);
    await page.fill('[data-testid="stemma-search"]', "Wren");
    await page.keyboard.press("Enter");
    await expect(mirror).toContainText("Prince Caelum (transmigration, Chapter IV)");
  });

  test("lifecycle: Stemma → Dossier → Stemma ×3 leaves exactly one instance and ≤1 layout; leaving the work leaves none", async ({ page }) => {
    await openStemma(page, 2);
    const reg = () => page.evaluate(() => { const r = (window as unknown as { __storyweaveCy: { instances: number; layouts: number; created: number } }).__storyweaveCy; return { i: r.instances, l: r.layouts, c: r.created }; });
    for (let i = 0; i < 3; i++) {
      await page.click("text=Dossier");
      await page.waitForSelector('[data-testid="entity-main"]');
      await page.waitForTimeout(200);
      // the ego graph is a separate instance with no running layout (concentric is one-shot)
      const off = await reg();
      expect(off.l).toBe(0);
      expect(off.i).toBe(1);
      await page.click("text=The Stemma");
      await page.waitForSelector('[data-testid="stemma-cy"]');
      await page.waitForTimeout(200);
      const mid = await reg();
      expect(mid.i).toBe(1);
      expect(mid.l).toBeLessThanOrEqual(1); // one finite burst at most, never a stack of them
    }
    await page.waitForTimeout(1400); // the burst ends
    const on = await reg();
    expect(on.i).toBe(1);
    expect(on.l).toBe(0);
    expect(on.c).toBeGreaterThanOrEqual(4);
    await page.goto("/#/");
    await page.waitForSelector('[data-testid="landing-root"]');
    await page.waitForTimeout(200);
    // R8: the Stemma's own instance is gone (this test's job), but the landing page
    // itself now mounts one cytoscape instance of its own (the try-it panel's mini-graph,
    // a `concentric`, non-continuous layout) — so "leaving the work" no longer means
    // "zero instances anywhere in the app", just "zero of the Stemma's".
    const gone = await reg();
    expect(gone.i).toBe(1);
    expect(gone.l).toBe(0);
  });

  // R9 regression: the camera fit landed off-screen after an in-app (SPA) navigation into
  // the Stemma tab, because a fresh mount whose focus resolves one render after the initial
  // (no-focus) graph triggers two cola bursts back-to-back, and cytoscape-cola's early
  // "convergence" layoutstop (measured: as little as 11ms into a 950ms burst, for a small
  // graph) was consuming the refit flag meant for the burst's real, later settle. Fixed in
  // StemmaCanvas.tsx (suppressNextStop + a layoutSettleMs elapsed-time gate). A plain
  // `page.goto`/reload always fit correctly (fresh mount, no double-burst race), so these
  // three tests specifically drive the SPA click paths that reproduced it.
  async function expectFocusFramed(page: Page): Promise<void> {
    // Longer than the 950ms burst + its 100ms epsilon, so the real (not premature) fit has
    // landed by the time this reads the camera.
    await page.waitForTimeout(1300);
    const state = await page.evaluate(() => {
      const cy = (window as unknown as {
        __storyweaveCy: { stemma: { nodes(sel: string): { [0]?: { renderedPosition(): { x: number; y: number } } }; width(): number; height(): number } };
      }).__storyweaveCy.stemma;
      const focus = cy.nodes(".focus")[0];
      const rp = focus ? focus.renderedPosition() : null;
      return { rp, w: cy.width(), h: cy.height() };
    });
    expect(state.rp, "a focused node is drawn").not.toBeNull();
    const { x, y } = state.rp!;
    // Not just "technically inside the canvas": within the padded, fitted region a correct
    // `animateFit` would have produced — a wrong fit crammed the focus into a far corner.
    expect(x, `focus x within the fitted canvas (0..${state.w})`).toBeGreaterThan(state.w * 0.1);
    expect(x).toBeLessThan(state.w * 0.9);
    expect(y, `focus y within the fitted canvas (0..${state.h})`).toBeGreaterThan(state.h * 0.1);
    expect(y).toBeLessThan(state.h * 0.9);
  }

  test("camera-fit regression: Dossier → Stemma tab click lands the focus framed, not off-screen", async ({ page }) => {
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "4"] as const);
    await page.reload();
    await page.waitForSelector('[data-testid="entity-main"]');
    await page.click("text=The Stemma");
    await page.waitForSelector('[data-testid="stemma-cy"]');
    await expectFocusFramed(page);
  });

  test("camera-fit regression: Chronicle → Stemma tab click lands the focus framed, not off-screen", async ({ page }) => {
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "4"] as const);
    await page.reload();
    await page.waitForSelector('[data-testid="entity-main"]');
    await page.click("text=Chronicle");
    await page.waitForSelector('[data-testid="stemma-footer"]', { state: "detached" }).catch(() => {});
    await page.click("text=The Stemma");
    await page.waitForSelector('[data-testid="stemma-cy"]');
    await expectFocusFramed(page);
  });

  test("camera-fit regression: landing → Explore the full book → Stemma tab click lands the focus framed", async ({ page }) => {
    await page.goto("/#/");
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "4"] as const);
    await page.reload();
    await page.waitForSelector('[data-testid="landing-root"]');
    await page.click('[data-testid="explore-full-book"]');
    await page.waitForSelector('[data-testid="entity-main"]');
    await page.click("text=The Stemma");
    await page.waitForSelector('[data-testid="stemma-cy"]');
    await expectFocusFramed(page);
  });
});

test.describe("Stemma — synthetic-100 (test-only fixture via interception)", () => {
  const fenced = (n: number) => ({
    slug: SLUG, n,
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

  test("Principal folds hidden members into their org with a +N badge counted from the fenced payload", async ({ page }) => {
    await openStemma(page, 4);
    const exp = drawn(fenced(4) as unknown as Payload);
    const got = await cyState(page);
    // independent fold count: visible = degree ≥ 2 | identity endpoint | focus(=principal)
    const principal = [...exp.degree.entries()].sort((a, b) => b[1] - a[1])[0]![0];
    const visible = new Set(exp.ids.filter((id) => (exp.degree.get(id) ?? 0) >= 2 || exp.idEnds.has(id) || id === principal));
    expect(got!.nodes).toEqual([...visible].sort());
    const fold = new Map<string, number>();
    for (const e of exp.edges) {
      if (!MEMBERSHIP.has(e.relation)) continue;
      const [member, org] = exp.nodes.get(e.target)?.type === "Organization" ? [e.source, e.target] : [e.target, e.source];
      if (exp.nodes.get(org)?.type !== "Organization") continue;
      if (visible.has(org) && !visible.has(member)) fold.set(org, (fold.get(org) ?? 0) + 1);
    }
    expect(fold.size).toBeGreaterThan(0);
    for (const [org, n] of fold) expect(got!.displays[org]).toBe(`${exp.nodes.get(org)!.label} +${n}`);
    // Everyone: all drawn, no badges
    await page.click('[data-testid="cast-everyone"]');
    await page.waitForTimeout(300);
    const all = await cyState(page);
    expect(all!.nodes).toEqual(exp.ids);
    for (const d of Object.values(all!.displays)) expect(d).not.toMatch(/\+\d+$/);
  });

  test("legibility: zero overlaps among principal labels at the default fit (synthetic-100 and the demo), at the 1280×720 minimum", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    for (const demo of [false, true]) {
      if (demo) await page.unroute(GRAPH_ROUTE_RE);
      await openStemma(page, 4);
      await page.click('[data-testid="clear-focus"]');
      await page.waitForTimeout(1600); // any burst has ended; the fit-all has run
      const overlaps = await page.evaluate(() => {
        const cy = (window as unknown as { __storyweaveCy: { stemma: { zoom(): number; nodes(): { filter(f: (n: never) => boolean): { map<T>(f: (n: never) => T): T[] } } } } }).__storyweaveCy.stemma;
        type N = { id(): string; style(k: string): string; boundingBox(o: object): { x1: number; y1: number; x2: number; y2: number } };
        const boxes = (cy.nodes() as unknown as { filter(f: (n: N) => boolean): { map<T>(f: (n: N) => T): T[] } })
          .filter((n) => n.style("label") !== "")
          .map((n) => ({ id: n.id(), b: n.boundingBox({ includeLabels: true, includeNodes: false, includeEdges: false, includeOverlays: false }) }));
        const z = cy.zoom();
        const out: string[] = [];
        for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
          const a = boxes[i]!.b, b = boxes[j]!.b;
          const ox = Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1);
          const oy = Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1);
          if (ox * z > 1 && oy * z > 1) out.push(`${boxes[i]!.id}×${boxes[j]!.id}`);
        }
        return { count: boxes.length, zoom: z, overlaps: out };
      });
      await test.info().attach(demo ? "labels-demo" : "labels-synthetic", { body: JSON.stringify(overlaps, null, 2), contentType: "application/json" });
      // the default fit must land in the default tier — otherwise labels are hidden and
      // this test would be measuring nothing
      expect(overlaps.zoom, "default fit is in the 0.5–1.5 tier").toBeGreaterThanOrEqual(0.5);
      // demo: every node labelled (13-node cast); synthetic: the LABEL_BUDGET minus deferrals
      // demo: the Principal cast at ch4 is ~7 nodes, all labelled; synthetic: LABEL_BUDGET minus deferrals
      expect(overlaps.count).toBeGreaterThan(demo ? 4 : 12);
      expect(overlaps.overlaps, demo ? "demo" : "synthetic").toEqual([]);
    }
  });

  test("R9 label legibility: principal-label effective size (font-size × zoom) ≥ 13px on the default (focused-on-principal) view at 1280×720", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const results: Record<string, unknown> = {};
    for (const demo of [false, true]) {
      if (demo) await page.unroute(GRAPH_ROUTE_RE);
      await openStemma(page, 4); // default view: focused on the principal, not cleared
      const measured = await page.evaluate(() => {
        const cy = (window as unknown as { __storyweaveCy: { stemma: { zoom(): number; nodes(sel: string): { filter(f: (n: never) => boolean): { map<T>(f: (n: never) => T): T[] } } } } }).__storyweaveCy.stemma;
        type N = { id(): string; data(k: string): unknown; style(k: string): string };
        const z = cy.zoom();
        // "Principal labels" = the base EB Garamond node label (§7.2, 17px), not the focus
        // node's own Pirata-One name overlay — measured on a labelled non-focus node so the
        // number reflects what §7.5 calls "all principal labels" at the default tier.
        const labelled = (cy.nodes(".near, .far") as unknown as { filter(f: (n: N) => boolean): { map<T>(f: (n: N) => T): T[] } })
          .filter((n) => n.style("label") !== "")
          .map((n) => ({ id: n.id(), label: n.data("display") as string, fontSize: parseFloat(n.style("font-size")) }));
        return { zoom: z, labelled };
      });
      const fontSize = measured.labelled[0]?.fontSize ?? 17;
      const effective = fontSize * measured.zoom;
      results[demo ? "demo" : "synthetic"] = { zoom: measured.zoom, fontSize, effective, sampleCount: measured.labelled.length };
      await test.info().attach("label-legibility", { body: JSON.stringify(results, null, 2), contentType: "application/json" });
      expect(measured.labelled.length, `${demo ? "demo" : "synthetic"}: at least one principal label drawn`).toBeGreaterThan(0);
      expect(effective, `${demo ? "demo" : "synthetic"}: effective principal-label size ≥ 13px`).toBeGreaterThanOrEqual(13);
    }
  });

  test("settle: positions stable within 1px within 1.5s of a filter change (synthetic-100)", async ({ page }) => {
    await openStemma(page, 4);
    await page.waitForTimeout(1500);
    const positions = () => page.evaluate(() => {
      const cy = (window as unknown as { __storyweaveCy: { stemma: { nodes(): { map<T>(f: (n: { id(): string; position(): { x: number; y: number } }) => T): T[] } } } }).__storyweaveCy.stemma;
      return Object.fromEntries(cy.nodes().map((n) => [n.id(), n.position()]));
    });
    const t0 = Date.now();
    await page.click('[data-testid="cast-everyone"]');
    await page.waitForTimeout(1200 - (Date.now() - t0));
    const a = await positions();
    await page.waitForTimeout(300);
    const b = await positions();
    let maxDelta = 0;
    for (const id of Object.keys(b)) {
      const p = a[id]; const q = b[id]!;
      if (!p) continue;
      maxDelta = Math.max(maxDelta, Math.hypot(p.x - q.x, p.y - q.y));
    }
    await test.info().attach("settle", { body: JSON.stringify({ nodes: Object.keys(b).length, maxDeltaPx: maxDelta }), contentType: "application/json" });
    expect(maxDelta).toBeLessThanOrEqual(1);
  });
});
