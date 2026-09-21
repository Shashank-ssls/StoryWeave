// The spoiler fence, tested at the UI layer (DESIGN_SPEC.md §9.1, rules F1-F9).
// The fence itself is enforced server-side (query/fence.py); these tests are the
// frontend's own invariant that it never asks for, caches, or displays more than the
// confirmed bookmark allows.
//
// Every rule below is `test.fixme` until the feature it depends on exists (the chapter
// bookmark model, Phase 3) — fixme keeps the gap visible in test output instead of the
// rule silently having no test at all. Un-fixme each one as its phase lands, per
// FRONTEND_OVERHAUL.md §5 Phase 3.

import { test } from "@playwright/test";

test.describe("Spoiler fence (DESIGN_SPEC §9.1)", () => {
  test.fixme(
    "F1 — no request above the confirmed bookmark, on every flow incl. rapid double confirm",
    async () => {},
  );
  test.fixme(
    "F2 — no entity/edge/reveal counts beyond the bookmark are ever displayed",
    async () => {},
  );
  test.fixme(
    "F3 — the sealed zone/row is a constant size; it does not scale with remaining content",
    async () => {},
  );
  test.fixme(
    "F4 — search / not-yet-met copy never confirms a name exists later",
    async () => {},
  );
  test.fixme(
    "F5 — moving the bookmark back purges cached payloads for chapters > new bookmark",
    async () => {},
  );
  test.fixme(
    "F6 — arc/volume names hidden until their start chapter <= bookmark",
    async () => {},
  );
  test.fixme("F7 — chapter titles, if added, follow F6", async () => {});
  test.fixme(
    "F8 — \"changed\" tag diffing uses only graph(n) and graph(n-1), both fenced",
    async () => {},
  );
  test.fixme(
    "F9 — demo/landing mini-graph obeys F1-F3, no hint of the upcoming reveal edge",
    async () => {},
  );
});
