// R9 §8.5 global keyboard map: `g d` / `g w` / `g c` chords and the `?` shortcut sheet.
// Handlers live in codex/shortcuts/useGlobalShortcuts.ts, mounted once at the app root
// (CodexApp) so they work from any of the three in-work screens.

import { test, expect } from "@playwright/test";

const SLUG = "the-hollow-crown";
const KEY = `storyweave:bookmark:${SLUG}`;

test.describe("Global keyboard map (§8.5)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/#/work/${SLUG}/entity/1`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "1"] as const);
    await page.reload();
    await page.waitForSelector('[data-testid="entity-main"]');
  });

  test("g d / g w / g c navigate the three tabs from anywhere in a work", async ({ page }) => {
    await page.keyboard.press("g");
    await page.keyboard.press("w");
    await expect(page).toHaveURL(new RegExp(`#/work/${SLUG}/web`));
    await page.keyboard.press("g");
    await page.keyboard.press("c");
    await expect(page).toHaveURL(new RegExp(`#/work/${SLUG}/chronicle`));
    await page.keyboard.press("g");
    await page.keyboard.press("d");
    await expect(page).toHaveURL(new RegExp(`#/work/${SLUG}/entity`));
  });

  test("a lone `g` with no follow-up key expires and does nothing", async ({ page }) => {
    await page.keyboard.press("g");
    await page.waitForTimeout(1100); // past the chord window
    await page.keyboard.press("w");
    // the `w` alone (chord expired) must not navigate
    await expect(page).toHaveURL(new RegExp(`#/work/${SLUG}/entity`));
  });

  test("`?` opens the shortcut sheet with a real focus trap; Esc closes it", async ({ page }) => {
    await page.keyboard.press("?");
    const sheet = page.locator('[data-testid="shortcut-sheet"]');
    await expect(sheet).toBeVisible();
    await expect(sheet).toContainText("g d");
    await expect(sheet).toContainText("Go to Dossier");
    // initial focus lands on the close button
    await expect(page.locator('[data-testid="shortcut-scrim"] button')).toBeFocused();
    // Tab wraps back to the only focusable control (a one-button trap)
    await page.keyboard.press("Tab");
    await expect(page.locator('[data-testid="shortcut-scrim"] button')).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(sheet).toHaveCount(0);
  });

  test("`?` and `g` do nothing while typing in an input (typing-target guard)", async ({ page }) => {
    await page.keyboard.press("g");
    await page.keyboard.press("w");
    await expect(page).toHaveURL(new RegExp(`#/work/${SLUG}/web`));
    await page.fill('[data-testid="stemma-search"]', "");
    await page.click('[data-testid="stemma-search"]');
    await page.keyboard.type("g?");
    await expect(page.locator('[data-testid="stemma-search"]')).toHaveValue("g?");
    await expect(page.locator('[data-testid="shortcut-sheet"]')).toHaveCount(0);
    await expect(page).toHaveURL(new RegExp(`#/work/${SLUG}/web`)); // no chord fired either
  });

  test("`?` does nothing while the Change-chapter dialog is open", async ({ page }) => {
    await page.click('[data-testid="change-chapter"]');
    await expect(page.locator('[data-testid="chapter-dialog"]')).toBeVisible();
    await page.keyboard.press("?");
    await expect(page.locator('[data-testid="shortcut-sheet"]')).toHaveCount(0);
    // the dialog's own Esc still works, unaffected
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="chapter-dialog"]')).toHaveCount(0);
  });
});
