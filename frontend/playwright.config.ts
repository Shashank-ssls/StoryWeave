import { defineConfig } from "@playwright/test";

// Local-only verification harness (FRONTEND_OVERHAUL.md §2 rule 2, §3).
// `channel: "chrome"` drives the machine's installed Chrome instead of a Playwright-
// managed download — the bundled Chromium download is blocked on this network, and this
// avoids it entirely with no behavioural difference for our purposes.
// The backend (uvicorn) is NOT started here — start it yourself via dev.ps1 first
// (see docs/design/FRONTEND_OVERHAUL.md §3 point 4 / SETUP_NOTES.md). `webServer` only
// boots the Vite dev server, and reuses one that's already running.
export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    channel: "chrome",
    headless: true,
    baseURL: "http://localhost:5173",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
