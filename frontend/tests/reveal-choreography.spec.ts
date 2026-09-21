// DESIGN_SPEC §8.2 choreography table, verified against real elapsed time (not
// Playwright's clock/`page.clock`): the reveal's timing is expressed as CSS `@keyframes` +
// `animation-delay` (RevealOverlay.module.css), which run on the compositor's own timeline
// and are unaffected by mocking `Date`/`setTimeout` — `page.clock` would freeze the
// choreography's visual state without ever advancing it. Real `waitForTimeout` at each
// sample point is the correct tool here; each element's computed `opacity` and `transform`
// are read at t = 0, 450, 1000, 1400ms and compared against the table.

import { test, expect, type Page } from "@playwright/test";

const SLUG = "the-hollow-crown";
const KEY = `storyweave:bookmark:${SLUG}`;

async function triggerReveal(page: Page): Promise<void> {
  await page.goto(`/#/work/${SLUG}/entity/1`);
  await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "1"] as const);
  await page.reload();
  await page.waitForSelector('[data-testid="chapter-row-bookmark"][data-chapter="1"]');
  await page.click('[data-testid="change-chapter"]');
  await page.fill('[data-testid="chapter-input"]', "2");
  await page.click('[data-testid="set-bookmark"]');
  await page.waitForSelector('[data-testid="reveal-overlay"]');
}

/** opacity, and the matrix's scaleX (index 0) / scaleY (index 3) components. */
async function state(page: Page, selector: string): Promise<{ opacity: number; scaleX: number; scaleY: number }> {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel) as HTMLElement | null;
    if (!el) return { opacity: -1, scaleX: -1, scaleY: -1 };
    const cs = getComputedStyle(el);
    const m = cs.transform === "none" ? [1, 0, 0, 1, 0, 0] : (cs.transform.match(/matrix\(([^)]+)\)/)?.[1].split(",").map(Number) ?? [1, 0, 0, 1, 0, 0]);
    return { opacity: Number(cs.opacity), scaleX: m[0]!, scaleY: m[3]! };
  }, selector);
}

test.describe("Reveal choreography (§8.2)", () => {
  test("full motion: t=0/450/1000/1400ms match the timing table", async ({ page }) => {
    await triggerReveal(page);

    // t=0: overlay just mounted — nothing past the base (pre-delay) authored state yet.
    let seal = await state(page, '[data-testid="reveal-connector"] > div:first-child');
    let thread = await state(page, '[data-testid="reveal-thread"]');
    let headline = await state(page, '[data-testid="reveal-headline"]');
    expect(seal.opacity).toBeLessThan(0.3); // 200ms delay hasn't elapsed
    expect(thread.scaleX).toBeLessThan(0.1); // 400ms delay hasn't elapsed
    expect(headline.opacity).toBeLessThan(0.3);

    // t=450ms: seals settled (delay 200 + duration 200 = 400 < 450); thread mid-draw
    // (delay 400, duration 500 -> ~10% through at 450); eye/headline/quote not started.
    await page.waitForTimeout(450);
    seal = await state(page, '[data-testid="reveal-connector"] > div:first-child');
    thread = await state(page, '[data-testid="reveal-thread"]');
    const eye1 = await state(page, '[data-testid="reveal-eye"]');
    headline = await state(page, '[data-testid="reveal-headline"]');
    expect(seal.opacity).toBeGreaterThan(0.9);
    expect(thread.scaleX).toBeGreaterThan(0.02);
    expect(thread.scaleX).toBeLessThan(0.8); // still drawing, not done
    expect(eye1.scaleY).toBeLessThan(0.2); // 900ms delay hasn't elapsed
    expect(headline.opacity).toBeLessThan(0.3);

    // t=1000ms (550ms later): thread finished (400+500=900 < 1000); eye opening (started
    // 900, duration 150 -> ~67% through); headline just starting (delay exactly 1000).
    await page.waitForTimeout(550);
    thread = await state(page, '[data-testid="reveal-thread"]');
    const eye2 = await state(page, '[data-testid="reveal-eye"]');
    const quote = await state(page, '[data-testid="reveal-quote"]');
    expect(thread.scaleX).toBeGreaterThan(0.95);
    expect(eye2.scaleY).toBeGreaterThan(0.3);
    expect(quote.opacity).toBeLessThan(0.3); // 1250ms delay hasn't elapsed

    // t=1400ms (400ms later): everything settled; buttons focusable, quote/caption visible.
    await page.waitForTimeout(400);
    const eye3 = await state(page, '[data-testid="reveal-eye"]');
    headline = await state(page, '[data-testid="reveal-headline"]');
    const quote2 = await state(page, '[data-testid="reveal-quote"]');
    expect(eye3.scaleY).toBeGreaterThan(0.9);
    expect(headline.opacity).toBeGreaterThan(0.9);
    expect(quote2.opacity).toBeGreaterThan(0.8);
    await expect(page.locator('[data-testid="reveal-open-dossier"]')).toBeFocused();
  });

  test("reduced motion: everything appears together with a single 200ms fade, no thread drawing, no mural brightening", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await triggerReveal(page);

    // Even very early, the thread is already at its FINAL shape (scaleX=1) — only its
    // opacity animates. Under full motion this would still be near 0 at this point.
    await page.waitForTimeout(60);
    const thread = await state(page, '[data-testid="reveal-thread"]');
    expect(thread.scaleX).toBeGreaterThan(0.95);

    await page.waitForTimeout(220); // past the single 200ms fade
    const seal = await state(page, '[data-testid="reveal-connector"] > div:first-child');
    const eye = await state(page, '[data-testid="reveal-eye"]');
    const headline = await state(page, '[data-testid="reveal-headline"]');
    const quote = await state(page, '[data-testid="reveal-quote"]');
    expect(seal.opacity).toBeGreaterThan(0.9);
    expect(eye.scaleY).toBeGreaterThan(0.9);
    expect(headline.opacity).toBeGreaterThan(0.9);
    expect(quote.opacity).toBeGreaterThan(0.9);
    await expect(page.locator('[data-testid="reveal-open-dossier"]')).toBeFocused();

    // §4.6 rule 5: the mural must never brighten under reduced motion.
    expect(await page.evaluate(() => document.documentElement.hasAttribute("data-reveal-active"))).toBe(false);
  });

  test("full motion DOES brighten the mural attribute for the overlay's duration only", async ({ page }) => {
    await triggerReveal(page);
    expect(await page.evaluate(() => document.documentElement.hasAttribute("data-reveal-active"))).toBe(true);
    await page.keyboard.press("Escape");
    await page.waitForSelector('[data-testid="reveal-overlay"]', { state: "detached" });
    expect(await page.evaluate(() => document.documentElement.hasAttribute("data-reveal-active"))).toBe(false);
  });
});
