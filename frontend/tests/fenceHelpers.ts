// Network-log helpers for the spoiler-fence tests (DESIGN_SPEC.md §9.1).
// Real use starts Phase 3 once the chapter/bookmark model exists; written now so the
// fence tests in fence.spec.ts can import a stable API from day one.

import { expect, type Page, type Request } from "@playwright/test";

export interface GraphRequestLog {
  /** Every /graph request URL seen since recording started. */
  urls: string[];
  /** Stop recording (detaches the page listener). */
  stop(): void;
}

/** The fenced graph route (R0 recon: `/api/v1/works/{slug}/graph?n={n}`). Anchored to the
 *  API path — a loose `includes("/graph")` also matched Vite serving `src/graph/diff.ts`
 *  (caught live at R3), which would have polluted the fence evidence. */
export const GRAPH_ROUTE_RE = /\/api\/v1\/works\/[^/?]+\/graph(\?|$)/;

/** Starts recording every fenced-graph API request the page makes. Call `.stop()` when done. */
export function recordGraphRequests(page: Page): GraphRequestLog {
  const urls: string[] = [];
  const onRequest = (req: Request): void => {
    const url = req.url();
    if (GRAPH_ROUTE_RE.test(url)) urls.push(url);
  };
  page.on("request", onRequest);
  return {
    urls,
    stop: () => page.off("request", onRequest),
  };
}

/** F1: none of the recorded `/graph` requests may ask for n greater than the bookmark. */
export function assertNoGraphRequestAbove(log: GraphRequestLog, bookmark: number): void {
  const offenders = log.urls.filter((url) => {
    const m = /[?&]n=(\d+)/.exec(url);
    return m !== null && Number(m[1]) > bookmark;
  });
  expect(offenders, `graph requests above bookmark n=${bookmark}`).toEqual([]);
}

/** R6: every forward step in the Hollow Crown demo legitimately reveals something, so a
 *  test that drives several forward moves in a row (Dossier's/Stemma's "walk" tests) would
 *  otherwise have its next click blocked by the reveal overlay's full-screen backdrop. The
 *  reveal UI itself is covered by reveal.spec.ts — here we just get it out of the way, the
 *  same way a reader would (Esc), so fence/content tests stay about fence/content. */
export async function dismissRevealIfShown(page: Page): Promise<void> {
  const overlay = page.locator('[data-testid="reveal-overlay"], [data-testid="reveal-summary-sheet"]');
  if ((await overlay.count()) > 0) {
    await page.keyboard.press("Escape");
    await overlay.first().waitFor({ state: "hidden" }).catch(() => {});
  }
}
