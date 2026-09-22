// R9 step 6 (DESIGN_SPEC.md §4.5 + §6.7): a focused reduced-motion audit. The reveal
// overlay's own reduced-motion choreography is already covered by
// reveal-choreography.spec.ts ("everything appears together with a single 200ms fade, no
// thread drawing"); this file covers the two pieces no suite had measured yet — the
// Stemma's cytoscape-cola physics burst (genuinely finite, not just visually calmer under
// `animate: false`) and the §6.7 loading glyph (static, in the literal ink/dim/faint
// order) — plus the global motion-duration tokens that back everything else.

import { test, expect, type Route } from "@playwright/test";
import { GRAPH_ROUTE_RE } from "./fenceHelpers";

const SLUG = "the-hollow-crown";
const KEY = `storyweave:bookmark:${SLUG}`;

test.describe("Reduced motion (§4.5)", () => {
  test("global motion-duration tokens collapse under prefers-reduced-motion: reduce", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/#/");
    const durs = await page.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      return {
        fast: cs.getPropertyValue("--dur-fast").trim(),
        base: cs.getPropertyValue("--dur-base").trim(),
        slow: cs.getPropertyValue("--dur-slow").trim(),
        reveal: cs.getPropertyValue("--dur-reveal").trim(),
      };
    });
    expect(durs).toEqual({ fast: "0ms", base: "0ms", slow: "200ms", reveal: "200ms" });
  });

  test("Stemma physics: the reduced-motion burst actually stops (positions stable within 1px, sampled after its own declared 800ms duration)", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/#/");
    await page.evaluate((k) => localStorage.removeItem(k), KEY);
    await page.goto(`/#/work/${SLUG}/web`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "4"] as const);
    await page.reload();
    await page.waitForFunction(() => !!(window as unknown as { __storyweaveCy?: { stemma: unknown } }).__storyweaveCy?.stemma);
    await page.waitForTimeout(900); // just past the reduced-motion burst's own 800ms budget
    const positions = () =>
      page.evaluate(() => {
        const cy = (window as unknown as { __storyweaveCy: { stemma: { nodes(): { map<T>(f: (n: { id(): string; position(): { x: number; y: number } }) => T): T[] } } } }).__storyweaveCy.stemma;
        return Object.fromEntries(cy.nodes().map((n) => [n.id(), n.position()]));
      });
    const a = await positions();
    await page.waitForTimeout(500);
    const b = await positions();
    let maxDelta = 0;
    for (const id of Object.keys(b)) {
      const p = a[id];
      const q = b[id]!;
      if (!p) continue;
      maxDelta = Math.max(maxDelta, Math.hypot(p.x - q.x, p.y - q.y));
    }
    await test.info().attach("settle", { body: JSON.stringify({ nodes: Object.keys(b).length, maxDeltaPx: maxDelta }), contentType: "application/json" });
    expect(maxDelta).toBeLessThanOrEqual(1);
  });

  test("loading glyph is static, in ink/dim/faint order, under reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.route(GRAPH_ROUTE_RE, async (route: Route) => {
      await new Promise((r) => setTimeout(r, 1500));
      await route.continue();
    });
    await page.goto(`/#/work/${SLUG}/chronicle`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "4"] as const);
    await page.reload();
    const dots = page.locator('[data-testid="loading-dots"] span');
    await expect(dots).toHaveCount(3);
    const styles = await dots.evaluateAll((els) =>
      els.map((el) => ({ animationName: getComputedStyle(el).animationName, background: getComputedStyle(el).backgroundColor })),
    );
    for (const s of styles) expect(s.animationName).toBe("none");
    expect(new Set(styles.map((s) => s.background)).size).toBe(3); // ink, dim, faint — three distinct colors, held still
    await expect(page.locator('[data-testid="chronicle-root"]')).toBeVisible({ timeout: 10_000 });
  });

  test("loading glyph fades in sequence (staggered) without reduced motion", async ({ page }) => {
    await page.route(GRAPH_ROUTE_RE, async (route: Route) => {
      await new Promise((r) => setTimeout(r, 1500));
      await route.continue();
    });
    await page.goto(`/#/work/${SLUG}/chronicle`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "4"] as const);
    await page.reload();
    const dots = page.locator('[data-testid="loading-dots"] span');
    await expect(dots).toHaveCount(3);
    const info = await dots.evaluateAll((els) =>
      els.map((el) => {
        const cs = getComputedStyle(el);
        return { name: cs.animationName, delay: cs.animationDelay, duration: cs.animationDuration };
      }),
    );
    for (const s of info) {
      expect(s.name).toContain("dotFade"); // CSS-modules-hashed keyframe name
      expect(s.duration).toBe("1.2s");
    }
    expect(new Set(info.map((s) => s.delay)).size).toBe(3); // each dot's fade starts at a different moment
    await expect(page.locator('[data-testid="chronicle-root"]')).toBeVisible({ timeout: 10_000 });
  });
});
