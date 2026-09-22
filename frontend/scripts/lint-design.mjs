#!/usr/bin/env node
// Static design-system checks (FRONTEND_OVERHAUL.md §4.3). Run via `npm run lint:design`.
//
// Checks, over every frontend/src/**/*.{ts,tsx,css} file:
//   1. no raw hex color outside tokens.css / the Cytoscape style module
//   2. no `var(--accent...)` outside the explicit red-permitted allow-list (DESIGN_SPEC
//      P2 / FRONTEND_OVERHAUL §2 rule 4 — red means reveal, nowhere else)
//   3. no literal `font-family:` outside tokens.css / the Cytoscape style module
//
// (R9 step 8: the legacy app — App.tsx, GraphView.tsx, Library.tsx, the old
// Composer.tsx, styles.css — was deleted whole, together with the `#/_legacy` route.
// This file used to carry two legacy-only mechanisms for that period — a LEGACY_FILES
// hex/font-family exemption list, and a rule-4 check for new class names colliding with
// the old global styles.css — both removed here along with the code they existed for.)
//
// RED_PERMITTED — files legitimately allowed to reference --accent. Not a "pending
// removal" list; these are meant to use accent permanently, per the red-discipline
// rule's own allow-list of contexts.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcRoot = path.resolve(__dirname, "..", "src");

// The ACTIVE Cytoscape style module: hex/font-family literals are allowed here by hard
// rule (§2 rule 6 — Cytoscape can't read CSS vars).
const CYTOSCAPE_STYLE_FILE = "codexStyle.ts";

const RED_PERMITTED = {
  "dev/TypeScale.tsx":
    "the hidden #/_type token gallery — must render the --accent/--accent-hi/" +
    "--accent-soft swatches to document them; never reader-facing.",
  "codex/Landing/Landing.module.css":
    "the landing kicker, the try-it stepper's dashed 'next' button, and the try-it " +
    "prompt row's eye glyph (§4.4: \"the eye glyph is the reveal marker\" — landing " +
    "try-it prompt named explicitly) — all three on DESIGN_SPEC §2's red-discipline " +
    "allow-list by name (landing kicker / next-stepper / reveal UI).",
  "codex/Dossier/Dossier.module.css":
    "identity kicker + the linked other name in the identity sentence (§6.2 item 5) and " +
    "the \"changed\" cast tag (§6.2 item 3) — all three named on the P2 allow-list.",
  "codex/Stemma/Stemma.module.css":
    "the Show checkboxes' accent-color (P2 allow-list: \"checkbox accent-color in the " +
    "Stemma filter\") and the identity selected-link kicker (§6.3 right panel).",
  "codex/chapter/ChapterDialog.module.css":
    "the dialog's \"current bookmark\" marker (DESIGN_SPEC §6.6 item 4 spells out " +
    "--accent for it; \"bookmark marker\" is on the P2 allow-list). One rule, one use.",
  "codex/reveal/RevealOverlay.module.css":
    "the reveal moment itself (§6.5): kicker, connector thread/glow, the linking word in " +
    "the headline — squarely \"reveal moments\" on the P2 allow-list.",
  "codex/reveal/RevealSummarySheet.module.css":
    "the jump-far summary sheet's per-row identity kicker (§8.1) — same reveal-moment " +
    "allowance as RevealOverlay, just listed instead of staged.",
  "codex/reveal/RevealChrome.module.css":
    "the quiet-mode toast's identity/deepen kicker (§8.2 \"Reveal quietly\" preference) " +
    "— the same reveal content, just delivered as a toast instead of an overlay.",
  "codex/Chronicle/Chronicle.module.css":
    "identity links + their ringed dots/labels, the bookmark line + its label, and the " +
    "selected-reveal kicker/capsule (§6.4) — identity edges, reveal UI and the bookmark " +
    "marker are all named on the P2 allow-list.",
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
  const redPermittedReason = RED_PERMITTED[rel];

  if (!isTokensCss && !isCytoscapeStyleFile) {
    const hex = text.match(HEX_RE);
    if (hex) failures.push(`${rel}: ${hex.length} raw hex color(s) — ${hex.slice(0, 3).join(", ")}${hex.length > 3 ? ", ..." : ""}`);
  }

  if (!redPermittedReason) {
    const accent = text.match(ACCENT_RE);
    if (accent) failures.push(`${rel}: ${accent.length} use(s) of var(--accent...) outside the red-permitted allow-list`);
  }

  if (!isTokensCss && !isCytoscapeStyleFile) {
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
    `Red-permitted: ${Object.keys(RED_PERMITTED).length} file(s).`,
);
