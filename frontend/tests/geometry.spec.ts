// Layout geometry assertions (FRONTEND_OVERHAUL.md §5 Phase 2 / R2 verification):
// measured rail widths / bar heights / paddings against DESIGN_SPEC.md §6.1-§6.4, at both
// the drawn width (1440) and the 1280-1439 breakpoint (tokens.css's own override values).
// Content is placeholder this phase, so only geometry is asserted here.

import { test, expect } from "@playwright/test";

const SLUG = "the-hollow-crown";

async function widthOf(page: import("@playwright/test").Page, selector: string): Promise<number> {
  const box = await page.locator(selector).first().boundingBox();
  if (!box) throw new Error(`no bounding box for ${selector}`);
  return Math.round(box.width);
}

test.describe("Dossier geometry (§6.2)", () => {
  test("rail 290 / right panel 400 at 1440", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await page.waitForSelector('[data-testid="dossier-root"]');
    expect(await widthOf(page, '[data-testid="dossier-rail"]')).toBe(290);
    expect(await widthOf(page, '[data-testid="dossier-right-panel"]')).toBe(400);
  });

  test("rail 260 / right panel 320 at the 1280-1439 breakpoint", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await page.waitForSelector('[data-testid="dossier-root"]');
    expect(await widthOf(page, '[data-testid="dossier-rail"]')).toBe(260);
    expect(await widthOf(page, '[data-testid="dossier-right-panel"]')).toBe(320);
  });
});

test.describe("Stemma geometry (§6.3)", () => {
  test("rail 290 / right panel 350 at 1440", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/#/work/${SLUG}/web`);
    await page.waitForSelector('[data-testid="stemma-root"]');
    expect(await widthOf(page, '[data-testid="stemma-rail"]')).toBe(290);
    expect(await widthOf(page, '[data-testid="stemma-right-panel"]')).toBe(350);
  });

  test("rail 260 / right panel 320 at the 1280-1439 breakpoint", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(`/#/work/${SLUG}/web`);
    await page.waitForSelector('[data-testid="stemma-root"]');
    expect(await widthOf(page, '[data-testid="stemma-rail"]')).toBe(260);
    expect(await widthOf(page, '[data-testid="stemma-right-panel"]')).toBe(320);
  });
});

// R7 removed the Chronicle route, so its geometry test went with it.

test.describe("No horizontal scroll at 1280x720", () => {
  for (const [name, hash] of [
    ["landing", "#/"],
    ["dossier", `#/work/${SLUG}/entity/1`],
    ["stemma", `#/work/${SLUG}/web`],
  ] as const) {
    test(name, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 720 });
      await page.goto(`/${hash}`);
      await page.waitForSelector("body");
      const { scrollWidth, clientWidth } = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
    });
  }
});

// R9 §11 responsive: 1024-1279 the Dossier/Stemma right panels
// become toggle drawers (closed by default, off-canvas); below 1024 the Dossier/Stemma
// rail becomes a top drawer too, single column. Shot widths per the brief: 1100 (inside
// the drawer breakpoint) and 900 (below the single-column breakpoint).
test.describe("R9 responsive: no horizontal scroll at 1100x800 and 900x800", () => {
  for (const width of [1100, 900]) {
    for (const [name, hash] of [
      ["dossier", `#/work/${SLUG}/entity/1`],
      ["stemma", `#/work/${SLUG}/web`],
    ] as const) {
      test(`${name} @ ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 800 });
        await page.goto(`/${hash}`);
        await page.waitForSelector("body");
        const { scrollWidth, clientWidth } = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        }));
        expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
      });
    }
  }
});

test.describe("R9 responsive: drawer toggles", () => {
  test("Dossier: right panel is off-canvas by default at 1100px, opens/closes via toggle + scrim", async ({ page }) => {
    await page.setViewportSize({ width: 1100, height: 800 });
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await page.waitForSelector('[data-testid="dossier-root"]');
    const panel = page.locator('[data-testid="dossier-right-panel"]');
    expect((await panel.boundingBox())!.x).toBeGreaterThanOrEqual(1100); // off-canvas (translated right)
    await page.click('[data-testid="panel-toggle"]');
    await expect.poll(async () => (await panel.boundingBox())!.x).toBeLessThan(1100);
    await page.click('[data-testid="panel-scrim"]');
    await expect.poll(async () => (await panel.boundingBox())!.x).toBeGreaterThanOrEqual(1100);
  });

  test("Dossier: rail is a top drawer at 900px, off-canvas until toggled", async ({ page }) => {
    await page.setViewportSize({ width: 900, height: 800 });
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await page.waitForSelector('[data-testid="dossier-root"]');
    const rail = page.locator('[data-testid="dossier-rail"]');
    expect((await rail.boundingBox())!.y).toBeLessThan(0); // translated above the viewport
    await page.click('[data-testid="rail-toggle"]');
    await expect.poll(async () => (await rail.boundingBox())!.y).toBeGreaterThanOrEqual(0);
  });

});
