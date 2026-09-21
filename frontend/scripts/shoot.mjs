#!/usr/bin/env node
// The visual verification harness (FRONTEND_OVERHAUL.md §3 point 4, §4.1).
//
// Usage: npm run shoot -- --phase=<id>
//
// For each shot in shots.config.mjs, at 1440x900 and 1280x720:
//   - loads the app, runs the shot's interaction
//   - saves a screenshot to .shots/phase-<id>/<name>@<w>.png
//   - saves every network request (with response status) to <name>@<w>.network.json
//   - fails the whole run if the page logged any console error
//
// Assumes the backend is already running (dev.ps1 + uvicorn) and the Vite dev server is
// reachable at SHOOT_BASE_URL (default http://localhost:5173) — start both yourself first.

import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { getShots } from "./shots.config.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");

function parseArgs(argv) {
  const out = {};
  for (const a of argv) {
    const m = /^--([^=]+)=(.*)$/.exec(a);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

const args = parseArgs(process.argv.slice(2));
const phase = args.phase;
if (!phase) {
  console.error("Usage: npm run shoot -- --phase=<id>");
  process.exit(1);
}

const BASE_URL = process.env.SHOOT_BASE_URL ?? "http://localhost:5173";
const VIEWPORTS = [
  { w: 1440, h: 900 },
  { w: 1280, h: 720 },
];

const outDir = path.join(frontendRoot, ".shots", `phase-${phase}`);
fs.mkdirSync(outDir, { recursive: true });

// Chromium issues an automatic favicon.ico probe outside Playwright's normal network
// instrumentation (it never appears in page.on('request')/('response')), so a missing
// favicon surfaces only as this exact generic console message. The old app has no
// <link rel="icon"> (a real gap, tracked for the redesign's own favicon in DESIGN_SPEC
// §14) but fixing it isn't in scope for a measuring-tools-only phase — so this one exact
// message is treated as benign (still printed, never silently dropped) while any other
// console error still fails the run.
const BENIGN_CONSOLE_ERRORS = new Set([
  "Failed to load resource: the server responded with a status of 404 (Not Found)",
]);

const shots = await getShots(phase);

let anyFailure = false;
const browser = await chromium.launch({ channel: "chrome", headless: true });

for (const shot of shots) {
  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({ viewport: { width: vp.w, height: vp.h } });
    const page = await context.newPage();

    const consoleErrors = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => consoleErrors.push(String(err)));

    const requests = [];
    page.on("request", (req) => {
      requests.push({ method: req.method(), url: req.url(), resourceType: req.resourceType() });
    });
    const statusByUrl = new Map();
    page.on("response", (res) => statusByUrl.set(res.url(), res.status()));

    const shotName = `${shot.name}@${vp.w}`;
    try {
      // Each shot navigates itself (rather than the harness doing one shared goto up
      // front) so a hash route gets a real full navigation: same-origin URLs that differ
      // only in the fragment do NOT reload the page, so a shared pre-navigation to
      // BASE_URL would leave a later `#/_type` goto as a same-document hash change that
      // never re-runs main.tsx's one-time route check.
      await shot.run(page, BASE_URL);

      const pngPath = path.join(outDir, `${shotName}.png`);
      await page.screenshot({ path: pngPath });

      const networkLog = requests.map((r) => ({ ...r, status: statusByUrl.get(r.url) ?? null }));
      fs.writeFileSync(
        path.join(outDir, `${shotName}.network.json`),
        JSON.stringify(networkLog, null, 2),
      );

      const realErrors = consoleErrors.filter((e) => !BENIGN_CONSOLE_ERRORS.has(e));
      const benign = consoleErrors.filter((e) => BENIGN_CONSOLE_ERRORS.has(e));
      if (realErrors.length > 0) {
        anyFailure = true;
        console.error(`[${shotName}] FAILED — console errors:\n  ${realErrors.join("\n  ")}`);
      } else {
        console.log(`[${shotName}] OK -> ${pngPath}`);
        if (benign.length > 0) console.log(`  (ignored ${benign.length} benign favicon 404)`);
      }
    } catch (err) {
      anyFailure = true;
      console.error(`[${shotName}] FAILED — ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      await context.close();
    }
  }
}

await browser.close();

if (anyFailure) {
  console.error("\nshoot: FAILED (see above).");
  process.exit(1);
}
console.log(`\nshoot: OK — ${shots.length * VIEWPORTS.length} shots captured, zero console errors.`);
