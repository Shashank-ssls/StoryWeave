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

/** Starts recording every `/graph` request the page makes. Call `.stop()` when done. */
export function recordGraphRequests(page: Page): GraphRequestLog {
  const urls: string[] = [];
  const onRequest = (req: Request): void => {
    const url = req.url();
    if (url.includes("/graph")) urls.push(url);
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
