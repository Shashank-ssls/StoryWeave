import { defineConfig } from "vitest/config";

// Unit tests for pure modules only (FRONTEND_OVERHAUL.md §6: graph/diff, roman, bookmark
// validation). Browser-level tests live in tests/*.spec.ts and are Playwright's — they
// must never be collected here.
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
  },
});
