// Computed-style assertions (DESIGN_SPEC.md §4.2 / FRONTEND_OVERHAUL.md §4.2) — rules a
// screenshot can't reliably prove. Run against the #/_type token/primitive gallery
// (R1), since it's the one page guaranteed to exercise every token and primitive.

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/#/_type");
  await page.waitForSelector(".type-page");
});

test("Pirata One never renders below 28px", async ({ page }) => {
  const offenders = await page.evaluate(() => {
    const bad: string[] = [];
    document.querySelectorAll("body *").forEach((el) => {
      const cs = getComputedStyle(el);
      if (cs.fontFamily.includes("Pirata One")) {
        const size = parseFloat(cs.fontSize);
        if (size < 28) bad.push(`${el.tagName} @ ${size}px`);
      }
    });
    return bad;
  });
  expect(offenders).toEqual([]);
});

test("no uppercase text-transform with positive letter-spacing", async ({ page }) => {
  const offenders = await page.evaluate(() => {
    const bad: string[] = [];
    document.querySelectorAll("body *").forEach((el) => {
      const cs = getComputedStyle(el);
      const ls = parseFloat(cs.letterSpacing);
      if (cs.textTransform === "uppercase" && !Number.isNaN(ls) && ls > 0) {
        bad.push(el.tagName);
      }
    });
    return bad;
  });
  expect(offenders).toEqual([]);
});

test("border-radius is 0 everywhere except [data-round] elements", async ({ page }) => {
  const offenders = await page.evaluate(() => {
    const bad: string[] = [];
    document.querySelectorAll("body *").forEach((el) => {
      if (el.hasAttribute("data-round")) return;
      const cs = getComputedStyle(el);
      const radii = [
        cs.borderTopLeftRadius,
        cs.borderTopRightRadius,
        cs.borderBottomLeftRadius,
        cs.borderBottomRightRadius,
      ];
      if (radii.some((r) => r !== "" && r !== "0px")) {
        bad.push(`${el.tagName} radius=${radii.join(",")}`);
      }
    });
    return bad;
  });
  expect(offenders).toEqual([]);
});

test("Pirata One, EB Garamond and Alegreya Sans are actually loaded (not a fallback)", async ({
  page,
}) => {
  const loaded = await page.evaluate(async () => {
    await document.fonts.ready;
    return {
      pirataOne: document.fonts.check('28px "Pirata One"'),
      ebGaramond: document.fonts.check('16px "EB Garamond"'),
      alegreyaSans: document.fonts.check('14px "Alegreya Sans"'),
    };
  });
  expect(loaded.pirataOne).toBe(true);
  expect(loaded.ebGaramond).toBe(true);
  expect(loaded.alegreyaSans).toBe(true);
});

test("no horizontal page scroll at 1280x720", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
});
