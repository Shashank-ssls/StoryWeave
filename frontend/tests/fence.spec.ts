// The spoiler fence, tested at the UI layer (DESIGN_SPEC.md §9.1, rules F1-F9).
// The fence itself is enforced server-side (query/fence.py); these tests are the
// frontend's own invariant that it never asks for, caches, or displays more than the
// confirmed bookmark allows.
//
// R3 activates F1, F2, F3, F5 and the §8.1/§6.7 flow tests. Every network assertion
// attaches the recorded /graph request log to the test (see `attachLog`), so the phase
// report's "MEASURED" claim points at real evidence. F4/F6-F9 stay `test.fixme` with the
// phase that activates each in the name — the gap is visible in the test output rather
// than the rule silently having no test.

import { test, expect, type Page, type Route } from "@playwright/test";
import { recordGraphRequests, assertNoGraphRequestAbove, type GraphRequestLog } from "./fenceHelpers";

const SLUG = "the-hollow-crown";
const CHAPTERS = 4; // Hollow Crown demo length (live /works, verified at R0)
const KEY = `storyweave:bookmark:${SLUG}`;
const GRAPH_RE = /\/api\/v1\/works\/[^/]+\/graph\?n=\d+/;

function nOf(url: string): number {
  return Number(/[?&]n=(\d+)/.exec(url)?.[1]);
}

// R6: every forward step in this 4-chapter demo legitimately reveals something (Wren/
// Caelum at 2, Sparrow/Veris at 3, Wren/Caelum again — deepening — at 4), so a forward
// move now opens the reveal overlay/summary sheet over the rest of the UI. The tests below
// are about fetch/cache/abort/error mechanics, not the reveal UI itself (that's
// reveal.spec.ts) — this route handler strips identity edges from the fenced response so
// those forward moves stay "quiet" (plain toast) and the tests keep testing what they say
// they test. Install it FIRST; a test that also needs its own delay/failure route installs
// that SECOND and calls `route.fallback()` for the "let it through" path (Playwright runs
// routes most-recently-registered-first; `fallback()` passes to the one before it).
const IDENTITY_RELATIONS = new Set(["SAME_AS", "ALIAS", "SECRET_IDENTITY", "REINCARNATION", "TRANSMIGRATED_INTO"]);
async function stripReveals(route: Route): Promise<void> {
  const resp = await route.fetch();
  const body = (await resp.json()) as { elements: { edges: { data: { relation: string } }[] } };
  body.elements.edges = body.elements.edges.filter((e) => !IDENTITY_RELATIONS.has(e.data.relation));
  await route.fulfill({ response: resp, body: JSON.stringify(body) });
}

async function attachLog(log: GraphRequestLog, name = "graph-requests"): Promise<void> {
  await test.info().attach(name, {
    body: JSON.stringify(log.urls, null, 2),
    contentType: "application/json",
  });
}

async function openDossier(page: Page, stored?: string): Promise<void> {
  await page.goto(`/#/work/${SLUG}/entity/1`);
  if (stored !== undefined) {
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, stored] as const);
    await page.reload();
  }
  await page.waitForSelector('[data-testid="chapter-row-bookmark"]');
}

async function bookmarkOnScreen(page: Page): Promise<number> {
  return Number(await page.locator('[data-testid="chapter-row-bookmark"]').getAttribute("data-chapter"));
}

/** Opens the dialog, types `n`, confirms. Never touches the network itself. */
async function confirmChapter(page: Page, n: number): Promise<void> {
  await page.click('[data-testid="change-chapter"]');
  await page.fill('[data-testid="chapter-input"]', String(n));
  await page.click('[data-testid="set-bookmark"]');
}

async function waitForBookmark(page: Page, n: number): Promise<void> {
  await expect(page.locator('[data-testid="chapter-row-bookmark"]')).toHaveAttribute("data-chapter", String(n));
}

test.describe("Spoiler fence (DESIGN_SPEC §9.1)", () => {
  test.beforeEach(async ({ page }) => {
    // Fresh reader every test: no stored bookmark, so the default (chapter 1) applies.
    await page.goto("/#/");
    await page.evaluate((k) => localStorage.removeItem(k), KEY);
  });

  test("F1 — first visit defaults to chapter 1 and requests only n=1", async ({ page }) => {
    const log = recordGraphRequests(page);
    await openDossier(page);
    expect(await bookmarkOnScreen(page)).toBe(1);
    await expect.poll(() => log.urls.length).toBe(1);
    assertNoGraphRequestAbove(log, 1);
    await attachLog(log);
  });

  test("F1 — forward via the dialog requests exactly the confirmed chapter, never above", async ({ page }) => {
    await openDossier(page);
    const log = recordGraphRequests(page);
    await confirmChapter(page, 3);
    await waitForBookmark(page, 3);
    await page.waitForTimeout(400);
    // The confirm itself, then (R4, F8) n−1 for the "changed" tags — nothing else, nothing above.
    expect(log.urls.map(nOf)).toEqual([3, 2]);
    assertNoGraphRequestAbove(log, 3);
    await attachLog(log);
  });

  test("F1 — `]` opens the dialog prefilled with bookmark+1 and fetches nothing by itself", async ({ page }) => {
    await openDossier(page);
    const log = recordGraphRequests(page);
    await page.keyboard.press("]");
    await expect(page.locator('[data-testid="chapter-dialog"]')).toBeVisible();
    await expect(page.locator('[data-testid="chapter-input"]')).toHaveValue("2");
    await page.waitForTimeout(500);
    expect(log.urls).toEqual([]);
    // Esc cancels: still nothing requested, bookmark unchanged.
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="chapter-dialog"]')).toHaveCount(0);
    expect(await bookmarkOnScreen(page)).toBe(1);
    expect(log.urls).toEqual([]);
    await attachLog(log);
  });

  test("F1 — no request while typing in the dialog (incl. an out-of-range 2000)", async ({ page }) => {
    await openDossier(page);
    const log = recordGraphRequests(page);
    await page.click('[data-testid="change-chapter"]');
    const input = page.locator('[data-testid="chapter-input"]');
    await input.fill("");
    await input.type("2000");
    await expect(page.locator('[data-testid="chapter-invalid"]')).toBeVisible();
    await expect(page.locator('[data-testid="chapter-invalid"]')).toHaveText(`There are only ${CHAPTERS} chapters.`);
    await expect(page.locator('[data-testid="set-bookmark"]')).toBeDisabled();
    await input.press("Enter"); // Enter on an invalid value must not confirm either
    await expect(page.locator('[data-testid="chapter-dialog"]')).toBeVisible();
    await input.fill("abc"); // digits-only: stripped to empty
    await expect(input).toHaveValue("");
    await input.fill("4");
    await page.waitForTimeout(500);
    expect(log.urls).toEqual([]);
    await attachLog(log);
  });

  test("F1 — rapid double confirm: only the last confirmed chapter ever renders", async ({ page }) => {
    await openDossier(page);
    // Slow every graph response so both confirms are in flight together.
    await page.route(GRAPH_RE, async (route: Route) => {
      await new Promise((r) => setTimeout(r, nOf(route.request().url()) === 2 ? 1200 : 300));
      await route.continue();
    });
    const log = recordGraphRequests(page);
    await confirmChapter(page, 2);
    await confirmChapter(page, 3);
    await waitForBookmark(page, 3);
    await page.waitForTimeout(1500); // let the slow n=2 response land (it must be dropped)
    expect(await bookmarkOnScreen(page)).toBe(3);
    // Both confirms were legitimately ≤ their own confirmed value; the dropped n=2
    // response was never cached, so F8's n−1 fetch for the tags requests 2 again.
    // Nothing above 3, and the first request of each confirm is the confirmed chapter.
    expect(log.urls.map(nOf).sort()).toEqual([2, 2, 3]);
    assertNoGraphRequestAbove(log, 3);
    await attachLog(log);
  });

  test("§8.1 — confirm forward, then step back before it resolves: forward response never lands", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    await confirmChapter(page, 2);
    await waitForBookmark(page, 2);
    await page.route(GRAPH_RE, async (route: Route) => {
      await new Promise((r) => setTimeout(r, 1000));
      await route.fallback();
    });
    const log = recordGraphRequests(page);
    await confirmChapter(page, 4);
    await expect(page.locator('[data-testid="loading-wash"]')).toBeVisible();
    await page.keyboard.press("["); // back to 1 while n=4 is in flight
    await waitForBookmark(page, 1);
    await page.waitForTimeout(1500);
    expect(await bookmarkOnScreen(page)).toBe(1);
    // The n=4 request was made (legitimately, it was confirmed) but must have been
    // aborted / dropped: the bookmark never reached 4 and the toast is the backward one.
    await expect(page.locator('[data-testid="toast"]')).toHaveAttribute("data-kind", "backward");
    await attachLog(log);
  });

  test("§8.1 — a slow older response arriving after a newer one is dropped (interception with delays)", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    await confirmChapter(page, 2);
    await waitForBookmark(page, 2);
    await page.route(GRAPH_RE, async (route: Route) => {
      const n = nOf(route.request().url());
      await new Promise((r) => setTimeout(r, n === 4 ? 1500 : 100));
      await route.fallback();
    });
    const log = recordGraphRequests(page);
    await confirmChapter(page, 4); // slow, in flight
    await page.keyboard.press("["); // back to 1 at once: n=4 is aborted + token-invalidated
    await waitForBookmark(page, 1);
    await page.waitForTimeout(2000); // longer than the n=4 delay — if it could land, it would have by now
    expect(await bookmarkOnScreen(page)).toBe(1);
    expect(await page.evaluate((k) => localStorage.getItem(k), KEY)).toBe("1");
    // Only the aborted n=4 confirm hit the network: chapter 1 was cached from the initial
    // load (cache holds chapters <= bookmark, and 1 <= 1), so the backward move needed no request.
    expect(log.urls.map(nOf)).toEqual([4]);
    await attachLog(log);
  });

  test("§6.7 — failed fetch keeps the old data, shows the banner, bookmark unchanged", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    await confirmChapter(page, 3);
    await waitForBookmark(page, 3);
    await page.route(GRAPH_RE, async (route: Route) => {
      if (nOf(route.request().url()) === 4) await route.fulfill({ status: 500, body: "boom" });
      else await route.fallback();
    });
    const log = recordGraphRequests(page);
    await confirmChapter(page, 4);
    const banner = page.locator('[data-testid="error-banner"]');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Couldn't load Chapter IV — still showing Chapter III");
    expect(await bookmarkOnScreen(page)).toBe(3);
    expect(await page.evaluate((k) => localStorage.getItem(k), KEY)).toBe("3");
    await expect(page.locator('[data-testid="loading-wash"]')).toHaveCount(0);
    expect(log.urls.map(nOf)).toEqual([4]);
    await attachLog(log);
  });

  test("F2 / F3 — at most 5 rows, one sealed row of constant size, no future numbers beyond 'of N'", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    for (const n of [1, 2, 4]) {
      if (n > 1) {
        await confirmChapter(page, n);
        await waitForBookmark(page, n);
      }
      const rows = page.locator('[data-testid="chapter-list"] li');
      expect(await rows.count()).toBeLessThanOrEqual(5);
      const sealed = page.locator('[data-testid="chapter-row-sealed"]');
      if (n < CHAPTERS) {
        await expect(sealed).toHaveCount(1);
        await expect(sealed).toHaveAttribute("data-chapter", String(n + 1));
        const box = await sealed.boundingBox();
        expect(Math.round(box?.height ?? 0)).toBe(44); // F3: fixed row height regardless of remaining chapters
      } else {
        await expect(sealed).toHaveCount(0); // last chapter: nothing left to seal
      }
      // F2: the only number > bookmark+1 on the list is the book length itself.
      const text = await page.locator('[data-testid="chapter-list"]').innerText();
      expect(text).toContain(`of ${CHAPTERS}`);
      const numbers = (text.match(/\b\d+\b/g) ?? []).map(Number);
      for (const k of numbers) expect(k === CHAPTERS || k <= n + 1).toBe(true);
    }
  });

  test("F5 — moving back purges cached chapters > new bookmark (re-forward refetches)", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    await confirmChapter(page, 3);
    await waitForBookmark(page, 3);
    const log = recordGraphRequests(page);
    await page.keyboard.press("[");
    await waitForBookmark(page, 2);
    await expect(page.locator('[data-testid="toast"]')).toContainText("sealed again");
    // n=2 was never cached (we jumped 1→3), so the backward move fetches n=2 — fine, ≤ 2.
    assertNoGraphRequestAbove(log, 2);
    // Forward again to 3: if the purge failed, the cache would serve it silently with no
    // request. A fresh request for n=3 is the observable proof it was purged.
    const before = log.urls.length;
    await confirmChapter(page, 3);
    await waitForBookmark(page, 3);
    expect(log.urls.slice(before).map(nOf)).toEqual([3]);
    await attachLog(log);
  });

  test("F5 — `[` at chapter 1 is a no-op (no request, no toast)", async ({ page }) => {
    await openDossier(page);
    const log = recordGraphRequests(page);
    await page.keyboard.press("[");
    await page.waitForTimeout(400);
    expect(log.urls).toEqual([]);
    await expect(page.locator('[data-testid="toast"]')).toHaveCount(0);
    await attachLog(log);
  });

  test("persistence — reload keeps the bookmark and requests only that chapter (+ n−1 for F8 tags)", async ({ page }) => {
    await openDossier(page);
    await confirmChapter(page, 3);
    await waitForBookmark(page, 3);
    const log = recordGraphRequests(page);
    await page.reload();
    await waitForBookmark(page, 3);
    await page.waitForTimeout(500);
    // Since R4 the model also fetches n−1 (here 2) for the "changed" tags — still ≤ bookmark.
    expect(log.urls.map(nOf).sort(), log.urls.join("\n")).toEqual([2, 3]);
    assertNoGraphRequestAbove(log, 3);
    await attachLog(log);
  });

  for (const bad of ["0", "-3", "999", "abc", "2.5", ""]) {
    test(`tampered localStorage "${bad}" resets to chapter 1 and requests only n=1`, async ({ page }) => {
      const log = recordGraphRequests(page);
      await openDossier(page, bad);
      expect(await bookmarkOnScreen(page)).toBe(1);
      await expect.poll(() => log.urls.filter((u) => GRAPH_RE.test(u)).length).toBeGreaterThan(0);
      assertNoGraphRequestAbove(log, 1);
      expect(await page.evaluate((k) => localStorage.getItem(k), KEY)).toBe("1");
      await attachLog(log);
    });
  }

  test("tab switch during a forward fetch: bookmark still commits, no extra request above it", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, async (route: Route) => {
      await new Promise((r) => setTimeout(r, 800));
      await route.continue();
    });
    const log = recordGraphRequests(page);
    await confirmChapter(page, 2);
    await page.click("text=The Stemma");
    await page.waitForSelector('[data-testid="stemma-root"]');
    // the Stemma rail (§6.3, R5) shows the bookmark in its footer rather than the compact list
    await expect(page.locator('[data-testid="stemma-footer"]')).toContainText("Read to Chapter II of 4");
    assertNoGraphRequestAbove(log, 2);
    await attachLog(log);
  });

  test("keys never fire inside inputs", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    await confirmChapter(page, 2);
    await waitForBookmark(page, 2);
    const log = recordGraphRequests(page);
    await page.click('[data-testid="change-chapter"]');
    const input = page.locator('[data-testid="chapter-input"]');
    await input.focus();
    await page.keyboard.press("[");
    await page.keyboard.press("]");
    await page.waitForTimeout(300);
    expect(log.urls).toEqual([]);
    await page.keyboard.press("Escape");
    expect(await bookmarkOnScreen(page)).toBe(2);
    await attachLog(log);
  });

  test("dialog: clicking a past row fills the input; Esc cancels without fetching", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    await confirmChapter(page, 3);
    await waitForBookmark(page, 3);
    const log = recordGraphRequests(page);
    await page.click('[data-testid="change-chapter"]');
    await page.locator('[data-testid="dialog-row-read"]').first().click();
    await expect(page.locator('[data-testid="chapter-input"]')).toHaveValue("1");
    await page.keyboard.press("Escape");
    expect(log.urls).toEqual([]);
    expect(await bookmarkOnScreen(page)).toBe(3);
  });

  test("dialog: focus is trapped; Tab from the last control wraps to the first", async ({ page }) => {
    await openDossier(page);
    await page.click('[data-testid="change-chapter"]');
    const dialog = page.locator('[data-testid="chapter-dialog"]');
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press("Tab");
      const inside = await page.evaluate(() => !!document.activeElement?.closest('[data-testid="chapter-dialog"]'));
      expect(inside).toBe(true);
    }
    await expect(dialog).toBeVisible();
  });

  test("§6.7 — banner 'Try again' re-requests exactly the failed chapter; any move clears the banner", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, stripReveals);
    await confirmChapter(page, 2);
    await waitForBookmark(page, 2);
    let fail = true;
    await page.route(GRAPH_RE, async (route: Route) => {
      if (fail && nOf(route.request().url()) === 3) await route.fulfill({ status: 500, body: "boom" });
      else await route.fallback();
    });
    await confirmChapter(page, 3);
    await expect(page.locator('[data-testid="error-banner"]')).toBeVisible();
    const log = recordGraphRequests(page);
    await page.click('[data-testid="banner-retry"]'); // still failing
    await expect(page.locator('[data-testid="error-banner"]')).toBeVisible();
    expect(await bookmarkOnScreen(page)).toBe(2);
    await page.keyboard.press("["); // moving back clears the banner and never retries 3
    await waitForBookmark(page, 1);
    await expect(page.locator('[data-testid="error-banner"]')).toHaveCount(0);
    await page.waitForTimeout(400);
    expect(log.urls.map(nOf)).toEqual([3]); // the one retry, nothing else (1 was cached)
    fail = false;
    await attachLog(log);
  });

  test("navigating away (browser back) during a forward fetch: aborted, nothing commits, return refetches only the bookmark", async ({ page }) => {
    await openDossier(page);
    await page.route(GRAPH_RE, async (route: Route) => {
      if (nOf(route.request().url()) === 3) await new Promise((r) => setTimeout(r, 1000));
      await route.continue();
    });
    const log = recordGraphRequests(page);
    await confirmChapter(page, 3);
    await page.goBack(); // to the landing hash: the provider unmounts, in-flight n=3 is invalidated
    await page.waitForSelector('[data-testid="landing-root"]');
    await page.waitForTimeout(1500);
    expect(await page.evaluate((k) => localStorage.getItem(k), KEY)).toBe("1");
    await page.goForward();
    await waitForBookmark(page, 1);
    await page.waitForTimeout(300);
    // n=3 (the confirm, aborted), then n=1 twice: R8's landing try-it panel (its own
    // ChapterProvider for the same demo slug) fetches once on mounting the landing hash,
    // and the Dossier's own remount on goForward fetches again independently. Never 3
    // again, and never anything above the bookmark from either provider.
    expect(log.urls.map(nOf)).toEqual([3, 1, 1]);
    await attachLog(log);
  });

  test("unknown work: chapter_count unresolvable → zero graph requests, controls disabled", async ({ page }) => {
    const log = recordGraphRequests(page);
    await page.goto("/#/work/no-such-book/entity/1");
    await page.waitForSelector('[data-testid="dossier-root"]');
    await expect(page.locator('[data-testid="change-chapter"]')).toBeDisabled();
    await page.keyboard.press("]");
    await page.keyboard.press("[");
    await page.waitForTimeout(600);
    expect(log.urls).toEqual([]);
    await expect(page.locator('[data-testid="chapter-dialog"]')).toHaveCount(0);
    await attachLog(log);
  });

  test("F4 (dossier, R4) — an entity not yet met shows neutral copy that never confirms a later appearance", async ({ page }) => {
    // Lady Veris (id 12) is first revealed in chapter 3; visit her dossier at chapter 2.
    await page.goto(`/#/work/${SLUG}/entity/12`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "2"] as const);
    await page.reload();
    const card = page.locator('[data-testid="state-not-present"]');
    await expect(card).toBeVisible();
    const text = (await card.innerText()).toLowerCase();
    expect(text).toContain("no one by that name, as of chapter ii.");
    expect(text).not.toContain("veris");
    expect(text).not.toMatch(/appears? later|later chapter|not yet|will appear/);
    expect(await page.locator('[data-testid="entity-main"]').count()).toBe(0);
  });
  test("F4 (search, R8) — Stemma search no-match copy never confirms a name exists later", async ({ page }) => {
    await page.goto(`/#/work/${SLUG}/web`);
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "2"] as const);
    await page.reload();
    await page.waitForSelector('[data-testid="stemma-footer"]');
    await page.fill('[data-testid="stemma-search"]', "Veris"); // first revealed chapter 3
    const card = page.locator('[data-testid="search-no-match"]');
    await expect(card).toBeVisible();
    const text = (await card.innerText()).toLowerCase();
    expect(text).toContain("no one by that name, as of chapter ii.");
    expect(text).not.toContain("veris");
    expect(text).not.toMatch(/appears? later|later chapter|not yet|will appear/);
  });
  test("F6 (integration phase) — arc names hidden until start <= bookmark, range always visible", async ({ page }) => {
    // the-ninth-house is the only demo work with arcs configured (D6); Hollow Crown
    // has none, which is exactly the blocks-of-100 fallback path (already covered
    // by every other dialog test in this file, all running against SLUG).
    const NH_SLUG = "the-ninth-house";
    const NH_KEY = `storyweave:bookmark:${NH_SLUG}`;
    const ARCS_RE = /\/api\/v1\/works\/[^/]+\/arcs\?n=\d+/;
    const arcLog: string[] = [];
    page.on("request", (req) => { if (ARCS_RE.test(req.url())) arcLog.push(req.url()); });

    // Bookmark 5: inside Arc 1 (ch1-8, "The Mourning Bell"), well before Arc 2
    // (ch9-16, "The Salt Cipher") starts.
    await page.goto(`/#/work/${NH_SLUG}`); // no entity id — PENDING_ENTITY resolves to the principal
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [NH_KEY, "5"] as const);
    // The arcs fetch (its own effect, keyed on bookmark) lands after the dossier's
    // own render — wait for it rather than racing it. Registered before the reload
    // that triggers it, so the response can't resolve before we start watching.
    const arcsAt5 = page.waitForResponse((r) => ARCS_RE.test(r.url()) && r.url().includes("n=5"));
    await page.reload();
    await page.waitForSelector('[data-testid="chapter-row-bookmark"]');
    await arcsAt5;
    await page.click('[data-testid="change-chapter"]');
    const blocksAt5 = await page.locator('[data-testid="dialog-block"]').allInnerTexts();
    expect(blocksAt5[0]).toBe("The Mourning Bell"); // arc 1 started -> real name
    expect(blocksAt5[1]).toBe("Arc 2 · chapters 9–16"); // arc 2 not started -> redacted
    expect(blocksAt5.join(" ")).not.toContain("Salt Cipher"); // the name itself never leaks
    await page.click('[data-testid="dialog-cancel"]');

    // Cross into Arc 2 (bookmark 10) — its name should now appear.
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [NH_KEY, "10"] as const);
    const arcsAt10 = page.waitForResponse((r) => ARCS_RE.test(r.url()) && r.url().includes("n=10"));
    await page.reload();
    await page.waitForSelector('[data-testid="chapter-row-bookmark"]');
    await arcsAt10;
    await page.click('[data-testid="change-chapter"]');
    const blocksAt10 = await page.locator('[data-testid="dialog-block"]').allInnerTexts();
    expect(blocksAt10[1]).toBe("The Salt Cipher");
    expect(blocksAt10[2]).toBe("Arc 3 · chapters 17–26"); // still redacted

    // F1 extends to /arcs too: never a request above the confirmed bookmark.
    for (const url of arcLog) {
      expect(Number(/[?&]n=(\d+)/.exec(url)?.[1])).toBeLessThanOrEqual(10);
    }
  });
  test.fixme("F7 (R7) — chapter titles, if added, follow F6 (no chapter-title feature exists yet)", async () => {});
  test("F8 (R4) — \"changed\" tags come from graph(n) and graph(n−1) only: exactly those two requests, both fenced", async ({ page }) => {
    const log = recordGraphRequests(page);
    await openDossier(page, "3");
    await expect(page.locator('[data-testid="changed-tag"]').first()).toBeVisible();
    await page.waitForTimeout(400);
    expect(log.urls.map(nOf).sort()).toEqual([2, 3]);
    assertNoGraphRequestAbove(log, 3);
    // the tags name exactly the chapter-3 arrivals (Sparrow + Veris), nobody else
    const tagged = await page.locator('[data-testid="cast-row"]:has([data-testid="changed-tag"])').evaluateAll((els) => els.map((e) => e.getAttribute("data-entity")).sort());
    expect(tagged).toEqual(["11", "12"]);
    await attachLog(log);
  });
  test("F9 (R8) — demo/landing mini-graph obeys F1-F3, no hint of the upcoming reveal edge", async ({ page }) => {
    const log = recordGraphRequests(page);
    await page.goto("/#/");
    await page.evaluate(([k, v]) => localStorage.setItem(k, v), [KEY, "1"] as const);
    await page.reload();
    await page.waitForSelector('[data-testid="landing-mini-graph"]');
    await page.waitForTimeout(300);
    // ch.2 introduces Prince Caelum and the Wren/Caelum identity edge — neither may exist
    // in the DOM (mini-graph or otherwise) while the landing bookmark is still ch.1.
    const nodeIds = (await page.locator('[data-testid="landing-mini-graph"]').getAttribute("data-nodes"))?.split(",") ?? [];
    const edgeIds = (await page.locator('[data-testid="landing-mini-graph"]').getAttribute("data-edges"))?.split(",") ?? [];
    expect(nodeIds).not.toContain("7"); // Prince Caelum
    expect(edgeIds).not.toContain("e12"); // the SECRET_IDENTITY edge, revealed ch.2
    expect(await page.evaluate(() => document.body.innerText)).not.toContain("Prince Caelum");
    assertNoGraphRequestAbove(log, 1);
    await attachLog(log);
  });
});
