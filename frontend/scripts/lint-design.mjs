#!/usr/bin/env node
// Static design-system checks (FRONTEND_OVERHAUL.md §4.3). Run via `npm run lint:design`.
//
// Checks, over every frontend/src/**/*.{ts,tsx,css} file:
//   1. no raw hex color outside tokens.css / the Cytoscape style module
//   2. no `var(--accent...)` outside the explicit red-permitted allow-list (DESIGN_SPEC
//      P2 / FRONTEND_OVERHAUL §2 rule 4 — red means reveal, nowhere else)
//   3. no literal `font-family:` outside tokens.css / the Cytoscape style module
//   4. (R2) no new-code class name also defined in the legacy stylesheet — see the
//      "CSS collision rule" note below.
//
// Two DIFFERENT allow-lists, for two different reasons — do not merge them:
//   LEGACY_FILES — old (pre-redesign) files not yet replaced, each naming the redesign
//     phase that removes it. Whole-file, not line-level (a static grep can't tell an old
//     line from a new one in the same file) — this is why "new code gets zero exemptions"
//     means new files, not new lines added to an already-legacy file. Shrinks only.
//   RED_PERMITTED — files legitimately allowed to reference --accent. Not a "pending
//     removal" list; these are meant to use accent permanently, per the red-discipline
//     rule's own allow-list of contexts.
//
// As of R2, the legacy app (App.tsx, GraphView.tsx, Library.tsx, Composer.tsx,
// styles.css, ontology.ts's old color constants) is reachable ONLY via the `#/_legacy`
// route (LegacyRoute.tsx loads styles.css lazily, only there) — so none of it shrinks
// piecemeal as new screens land; it is deleted whole, together with `#/_legacy` itself,
// at R9. (The R1 report guessed a piecemeal timeline for styles.css/ontology.ts before
// `#/_legacy` existed — corrected here now that the real mechanism is in place.)

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcRoot = path.resolve(__dirname, "..", "src");

// The ACTIVE Cytoscape style module: hex/font-family literals are allowed here by hard
// rule (§2 rule 6 — Cytoscape can't read CSS vars). Ported at R4 (pulled forward from
// R5 for the Dossier's ego graph); GraphView.tsx, the old stylesheet, moved to
// LEGACY_FILES at the same time.
const CYTOSCAPE_STYLE_FILE = "codexStyle.ts";

const LEGACY_FILES = {
  "GraphView.tsx":
    "R9 — the old Cytoscape view (its own inline hex stylesheet), reachable only via " +
    "#/_legacy; deleted whole with the legacy route.",
  "ontology.ts":
    "R9 — TYPE_COLOR/REVEAL/GROUND/INK/INK_DIM/EDGE_QUIET only serve the old " +
    "GraphView.tsx Cytoscape stylesheet, reachable only via #/_legacy as of R2; removed " +
    "together with the legacy route at R9.",
  "styles.css":
    "R9 — the old app's global stylesheet, loaded only by LegacyRoute.tsx for #/_legacy " +
    "as of R2 (no longer globally imported); deleted whole alongside the legacy route.",
};

const RED_PERMITTED = {
  "dev/TypeScale.tsx":
    "the hidden #/_type token gallery — must render the --accent/--accent-hi/" +
    "--accent-soft swatches to document them; never reader-facing.",
  "codex/Landing/Landing.module.css":
    "the landing kicker — explicitly on DESIGN_SPEC §2's red-discipline allow-list " +
    "(\"the landing kicker\" is named alongside identity edges/reveal UI/bookmark " +
    "marker/changed tags/next-stepper/Stemma filter as a permitted --accent use).",
  "codex/Dossier/Dossier.module.css":
    "identity kicker + the linked other name in the identity sentence (§6.2 item 5) and " +
    "the \"changed\" cast tag (§6.2 item 3) — all three named on the P2 allow-list.",
  "codex/Stemma/Stemma.module.css":
    "the Show checkboxes' accent-color (P2 allow-list: \"checkbox accent-color in the " +
    "Stemma filter\") and the identity selected-link kicker (§6.3 right panel).",
  "codex/chapter/ChapterDialog.module.css":
    "the dialog's \"current bookmark\" marker (DESIGN_SPEC §6.6 item 4 spells out " +
    "--accent for it; \"bookmark marker\" is on the P2 allow-list). One rule, one use.",
};

const HEX_RE = /#[0-9a-fA-F]{3,8}\b/g;
const ACCENT_RE = /var\(--accent/g;
// CSS declaration ("font-family: 'X'") or a quoted-key JS/CSS-in-JS property
// ("'font-family': 'X'") — NOT React's camelCase `fontFamily: "var(--x)"` inline style,
// which is the tokens-only pattern components are expected to use.
const FONT_FAMILY_LITERAL_RE = /font-family['"]?\s*:\s*['"`]/g;
const CLASS_SELECTOR_RE = /\.([a-zA-Z_][a-zA-Z0-9_-]*)/g;

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(p, out);
    else if (/\.(ts|tsx|css)$/.test(entry.name)) out.push(p);
  }
  return out;
}

function extractClassNames(cssText) {
  // Strip /* ... */ comments first — otherwise a comment like "DESIGN_SPEC.md" or
  // "tokens.css" reads as class selectors ".md"/".css" (caught live: both showed up as
  // bogus "collisions" before this fix).
  const withoutComments = cssText.replace(/\/\*[\s\S]*?\*\//g, "");
  const names = new Set();
  let m;
  while ((m = CLASS_SELECTOR_RE.exec(withoutComments))) names.add(m[1]);
  return names;
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

// 4. CSS collision rule (R2). Only PLAIN (non-module) CSS files are checked: a
// `.module.css` class name is hashed by Vite at build time, so it can never actually
// collide with anything at runtime regardless of what the source calls it — that's the
// point of using CSS Modules for every R2+ component, so checking them here would just be
// noise. Plain global CSS (tokens.css, the R1 primitives, this file's own future additions)
// is the part that's genuinely at risk, same as `.swatch` was in R1.
const legacyCssPath = path.join(srcRoot, "styles.css");
const legacyClassNames = extractClassNames(fs.readFileSync(legacyCssPath, "utf8"));

for (const file of files) {
  if (!file.endsWith(".css") || file.endsWith(".module.css")) continue;
  if (file === legacyCssPath) continue;
  const rel = path.relative(srcRoot, file).replace(/\\/g, "/");
  const names = extractClassNames(fs.readFileSync(file, "utf8"));
  const collisions = [...names].filter((n) => legacyClassNames.has(n));
  if (collisions.length > 0) {
    failures.push(`${rel}: class name(s) collide with legacy styles.css — ${collisions.join(", ")}`);
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
