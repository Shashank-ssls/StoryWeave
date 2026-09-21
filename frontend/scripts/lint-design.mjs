#!/usr/bin/env node
// Static design-system checks (FRONTEND_OVERHAUL.md §4.3). Run via `npm run lint:design`.
//
// Checks, over every frontend/src/**/*.{ts,tsx,css} file:
//   1. no raw hex color outside tokens.css / the Cytoscape style module
//   2. no `var(--accent...)` outside the explicit red-permitted allow-list (DESIGN_SPEC
//      P2 / FRONTEND_OVERHAUL §2 rule 4 — red means reveal, nowhere else)
//   3. no literal `font-family:` outside tokens.css / the Cytoscape style module
//
// Two DIFFERENT allow-lists, for two different reasons — do not merge them:
//   LEGACY_FILES — old (pre-redesign) files not yet replaced, each naming the redesign
//     phase that removes it. Whole-file, not line-level (a static grep can't tell an old
//     line from a new one in the same file) — this is why "new code gets zero exemptions"
//     means new files, not new lines added to an already-legacy file. Shrinks only.
//   RED_PERMITTED — files legitimately allowed to reference --accent. Not a "pending
//     removal" list; these are meant to use accent permanently, per the red-discipline
//     rule's own allow-list of contexts.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcRoot = path.resolve(__dirname, "..", "src");

// The Cytoscape style module: hex/font-family literals are allowed here by hard rule
// (§2 rule 6 — Cytoscape can't read CSS vars). Currently the old GraphView.tsx plays this
// role (its inline Cytoscape stylesheet); Phase 5 splits it into graph/codexStyle.ts,
// which then becomes the (only) exempt file in its place.
const CYTOSCAPE_STYLE_FILE = "GraphView.tsx";

const LEGACY_FILES = {
  "ontology.ts":
    "R5 — TYPE_COLOR/REVEAL/GROUND/INK/INK_DIM/EDGE_QUIET only serve the old Cytoscape " +
    "stylesheet; removed when Phase 5 ports codexStyle.ts.",
  "styles.css":
    "R2/R4/R5/R7/R8 (piecemeal) — the old app's global stylesheet; shrinks as each old " +
    "screen (shell chrome, graph canvas, library) is replaced, fully gone by R8 (Landing).",
};

const RED_PERMITTED = {
  "dev/TypeScale.tsx":
    "the hidden #/_type token gallery — must render the --accent/--accent-hi/" +
    "--accent-soft swatches to document them; never reader-facing.",
};

const HEX_RE = /#[0-9a-fA-F]{3,8}\b/g;
const ACCENT_RE = /var\(--accent/g;
// CSS declaration ("font-family: 'X'") or a quoted-key JS/CSS-in-JS property
// ("'font-family': 'X'") — NOT React's camelCase `fontFamily: "var(--x)"` inline style,
// which is the tokens-only pattern components are expected to use.
const FONT_FAMILY_LITERAL_RE = /font-family['"]?\s*:\s*['"`]/g;

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(p, out);
    else if (/\.(ts|tsx|css)$/.test(entry.name)) out.push(p);
  }
  return out;
}

const files = walk(srcRoot);
const failures = [];

for (const file of files) {
  const rel = path.relative(srcRoot, file).replace(/\\/g, "/");
  const base = path.basename(file);
  const text = fs.readFileSync(file, "utf8");

  const isTokensCss = base === "tokens.css";
  const isCytoscapeStyleFile = base === CYTOSCAPE_STYLE_FILE;
  const legacyReason = LEGACY_FILES[base];
  const redPermittedReason = RED_PERMITTED[rel];

  if (!isTokensCss && !isCytoscapeStyleFile && !legacyReason) {
    const hex = text.match(HEX_RE);
    if (hex) failures.push(`${rel}: ${hex.length} raw hex color(s) — ${hex.slice(0, 3).join(", ")}${hex.length > 3 ? ", ..." : ""}`);
  }

  if (!redPermittedReason) {
    const accent = text.match(ACCENT_RE);
    if (accent) failures.push(`${rel}: ${accent.length} use(s) of var(--accent...) outside the red-permitted allow-list`);
  }

  if (!isTokensCss && !isCytoscapeStyleFile && !legacyReason) {
    const literal = text.match(FONT_FAMILY_LITERAL_RE);
    if (literal) failures.push(`${rel}: literal font-family outside tokens.css/Cytoscape style file`);
  }
}

if (failures.length > 0) {
  console.error("lint:design FAILED:\n  " + failures.join("\n  "));
  process.exit(1);
}
console.log(
  `lint:design OK — ${files.length} files checked. ` +
    `Legacy allow-list: ${Object.keys(LEGACY_FILES).length} file(s). ` +
    `Red-permitted: ${Object.keys(RED_PERMITTED).length} file(s).`,
);
