// StoryWeave — Cytoscape stylesheet for "The Heretic's Codex" (DESIGN_SPEC.md §7).
// Ported from docs/design/cytoscape-style.js at R4 (FRONTEND_OVERHAUL.md §1).
//
// THE ONE FILE ALLOWED LITERAL HEX / FONT NAMES (§2 rule 6): Cytoscape's canvas renderer
// cannot read CSS custom properties, so the values below MIRROR src/styles/tokens.css.
// If a token changes there, change it here too — lint:design exempts only this file.
//
// Element data expected (built by graph/viewModel.ts + graph/stemmaModel.ts from the
// fenced /graph payload):
//   node.data: { id, label, display, kind: 'person'|'order'|'place'|'thing', degree,
//                initial, size, sizeFar }
//     `display` is the drawn label (label, or "label +N" for a folded org — §6.3 badge);
//     `size`/`sizeFar` are §7.1's clamp(16, 12 + 3·√degree, 34) and its 80% (§7.5 far tier),
//     computed in JS because Cytoscape mappers can't do sqrt/clamp.
//   edge.data: { id, source, target, kind: 'social'|'structural'|'identity', relation,
//                revealed_chapter, label, grade: 'STATED'|'INFERRED', arrow, thickness }
//     `label` is the plain-words relation with "(implied)" already appended for INFERRED;
//     `arrow` is 'triangle' only on the directed relations; `thickness` is weight in 3 steps.
// Classes the app toggles:
//   .focus (the focused node), .near (in focus set), .far (outside focus set),
//   .italic (orders/places/things labels), .selected-edge, .just-revealed (3s highlight),
//   .tier-far / .tier-close (§7.5), .identity-endpoint, .kbd-ring (§8.3 arrow-key cursor)

import type { Core, StylesheetStyle } from "cytoscape";

export const T = {
  bg: "#150B0A",
  deep: "#0C0605",
  line: "#3A2420",
  ink: "#E8D8C2",
  dim: "#A8917D",
  faint: "#6B5548",
  accent: "#D9503A",
  onInk: "#150B0A",
} as const;

const body = '"EB Garamond", Georgia, serif';
const display = '"Pirata One", Georgia, serif';

// Cytoscape's typings are stricter than its runtime (mapData strings, underlay-*), so the
// style objects are typed loosely here and cast once at the export.
type Style = { selector: string; style: Record<string, unknown> };

const styles: Style[] = [
  // ---- nodes: base ----
  {
    selector: "node",
    style: {
      width: 16,
      height: 16,
      "background-color": T.bg,
      "border-width": 1.4,
      "border-color": T.ink,
      label: "data(display)",
      "font-family": body,
      "font-size": 17,
      color: T.ink,
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 8,
      "text-outline-color": T.bg,
      "text-outline-width": 3,
      "min-zoomed-font-size": 9,
      "transition-property": "background-color, border-color, color, width, height",
      "transition-duration": "420ms",
    },
  },
  {
    selector: 'node[kind = "person"]',
    style: {
      shape: "ellipse",
      "background-color": T.ink,
      "border-width": 0,
      width: "data(size)",
      height: "data(size)",
    },
  },
  { selector: 'node[kind = "order"]', style: { shape: "ellipse" } },
  { selector: 'node[kind = "place"]', style: { shape: "rectangle" } },
  { selector: 'node[kind = "thing"]', style: { shape: "diamond", width: 20, height: 20 } },
  { selector: "node.italic", style: { "font-style": "italic" } },

  // ---- focus mode ----
  { selector: "node.far", style: { color: T.faint, "border-color": T.faint } },
  { selector: 'node.far[kind = "person"]', style: { "background-color": T.faint } },
  {
    selector: "node.focus",
    style: {
      width: 46,
      height: 46,
      "background-color": T.ink,
      "border-width": 7,
      "border-color": T.bg, // inner ring gap
      "outline-width": 1.5,
      "outline-color": T.ink,
      "outline-offset": 0, // outer ring (Cytoscape >= 3.28)
      label: "data(initial)",
      "font-family": display,
      "font-size": 22,
      color: T.onInk,
      "text-valign": "center",
      "text-margin-y": 0,
      "text-outline-width": 0,
    },
  },

  // ---- edges ----
  // R7: a line the reader cannot read is a line that teaches nothing, so the label is
  // ALWAYS on (v1 drew bare lines and put the relation in a hover tooltip, which does not
  // exist on a phone). `data(label)` is already in plain words and already carries the
  // "(implied)" suffix — see graph/viewModel.ts's `edgeLabel`.
  {
    selector: "edge",
    style: {
      "curve-style": "straight",
      width: "data(thickness)",
      "line-color": T.line,
      "target-arrow-shape": "data(arrow)",
      "target-arrow-color": T.dim,
      "arrow-scale": 0.8,
      label: "data(label)",
      "font-family": body,
      "font-size": 12,
      color: T.dim,
      "text-rotation": "autorotate",
      "text-outline-color": T.bg,
      "text-outline-width": 3,
      "text-background-color": T.bg,
      "text-background-opacity": 0.65,
      "text-background-padding": 2,
      "min-zoomed-font-size": 7,
      "transition-property": "line-color, width, opacity",
      "transition-duration": "420ms",
    },
  },
  // The grade IS the line style (rule 4 as amended): solid = the book states it in one
  // sentence; dashed = implied by context. Kept visually distinct from the old
  // `structural` dash by a longer pattern, so the two cannot be confused at a glance.
  {
    selector: 'edge[grade = "INFERRED"]',
    style: { "line-style": "dashed", "line-dash-pattern": [6, 5] },
  },
  { selector: 'edge[kind = "social"].near', style: { "line-color": T.dim } },
  { selector: 'edge[kind = "structural"]', style: { "line-color": T.line } },
  {
    selector: 'edge[kind = "identity"]',
    style: {
      "line-color": T.accent,
      color: T.accent,
      "underlay-color": T.accent,
      "underlay-opacity": 0.15,
      "underlay-padding": 5,
    },
  },
  { selector: 'edge[kind = "identity"].far', style: { opacity: 0.45 } },
  { selector: "edge.selected-edge", style: { width: 3.2, "underlay-opacity": 0.25 } },
  { selector: "edge.just-revealed", style: { "underlay-opacity": 0.35, "underlay-padding": 8 } },

  // ---- zoom tiers (§7.5) ----
  { selector: "node.tier-far", style: { label: "", width: "data(sizeFar)", height: "data(sizeFar)" } },
  { selector: "node.tier-far.focus", style: { label: "data(initial)", width: 46, height: 46 } },
  // §7.5 far tier keeps identity endpoints labelled — so they must also be exempt from
  // the base `min-zoomed-font-size: 9`, which would otherwise blank them below zoom ≈0.53.
  { selector: "node.tier-far.identity-endpoint", style: { label: "data(display)", "min-zoomed-font-size": 0 } },
  { selector: "node.tier-close", style: { color: T.ink } },
  // "principal labels" only at the default tier on large casts (stemmaModel.isMinorLabel)
  { selector: "node.label-minor, node.label-deferred", style: { label: "" } },
  // R7: an edge label that lost the collision pass. It returns at the close zoom tier and
  // whenever the edge is in the focus set — the words are deferred, never discarded.
  { selector: "edge.label-deferred", style: { label: "" } },
  { selector: "edge.label-deferred.near, edge.label-deferred.tier-close", style: { label: "data(label)" } },
  { selector: "node.label-minor.near, node.label-minor.tier-close, node.label-deferred.near, node.label-deferred.tier-close", style: { label: "data(display)" } },
  { selector: "node.tier-close.focus", style: { color: T.onInk } }, // the initial sits ON the ink disk

  // ---- step 0 (§8.3): the focus and its DIRECT ties only ----
  // The steps control has three settings: 0 draws nothing outside the 1-hop set, 1 draws
  // it dimmed at 1 hop, 2 at 2 hops. This is a DISPLAY clause applied after the fence
  // (retrofit rule 1) — the payload is identical at all three, so nothing here can leak.
  // `display: none` rather than opacity 0, so a hidden node is also unhittable: a reader
  // who asked to see only the direct ties cannot select something invisible by accident.
  // Declared last so it beats every other selector that sets a label or a colour.
  { selector: ".out-of-focus", style: { display: "none" } },

  // ---- keyboard cursor (§8.3): 2px ink ring on the neighbour under arrow-key focus ----
  { selector: "node.kbd-ring", style: { "outline-width": 2, "outline-color": T.ink, "outline-offset": 3 } },
];

export const codexStyle = styles as unknown as StylesheetStyle[];

// Zoom tiers (§7.5): call on 'zoom' events.
export function applyZoomTier(cy: Core): void {
  const z = cy.zoom();
  cy.batch(() => {
    // R7: edges carry the tier too, so a deferred relation label can come back when the
    // reader zooms in (`edge.label-deferred.tier-close` above).
    cy.elements().removeClass("tier-far tier-close");
    if (z < 0.5) cy.nodes().addClass("tier-far");
    else if (z > 1.5) cy.elements().addClass("tier-close");
  });
}

// Physics (§7.6) — used by the Stemma (R5); the Dossier's ego graph uses `concentric`.
// Deviation from the reference's `infinite: true`, measured at R5: an infinite cola run
// never actually settles after a filter change (105px of drift between t=1.2s and 1.5s
// on synthetic-100), so the Stemma runs physics as a finite burst after every data /
// filter change and again on drag-end. Dragging still pins the node while the burst
// runs; the graph re-settles around it; and "settles within 1.5s" is guaranteed rather
// than hoped for. Reduced motion: the spec's 800ms, then stop.
// 950ms: the burst starts a React render (~100ms) after the click that caused it and cola
// overshoots its budget by a tick or two, so this is what "settled within 1.5s" needs.
export const SETTLE_MS = 950;
// Spacing is tuned by cast size (§7.2 "tune cola nodeSpacing/edgeLength; verify by
// screenshot for the 13-node demo and a 100-node fixture"): the reference 40/140 reads
// well up to ~40 nodes; above that the fit-all could not land inside the default zoom
// tier on synthetic-100, so spacing tightens (measured at R5).
// R7 [MEASURED], 1280x720: the canvas is only 652x510 once the rail (290) and the right
// panel (350) are subtracted, and the R5 spacing spread the ch40 default cast of 20 over
// a 1331x1287 model box. Fitting that lands at zoom 0.462 -- under §7.5's 0.5 far-tier
// threshold, where node labels are blanked -- so the readable graph arrived with nobody's
// name on it. Small casts are therefore packed tighter, which is what lets a fit stay in
// the default tier on the minimum supported viewport. Re-measured after the change.
//
// R7, second measurement: the canvas at the 1280x720 minimum is 652x508 (landscape), and
// on the 20-node synthetic cast cola produced a 406x791 PORTRAIT layout inside it. The
// fit is then height-bound at zoom 0.571 — 17px labels render at 9.7px, under R9's 13px
// floor — with half the canvas width unused.
//
// Two levers were measured before the one that worked. Cola's own `boundingBox` option
// changed nothing (identical 406x791 layout). Cutting edge length 25% moved the height
// only 791 -> 735 and the zoom 0.571 -> 0.615, because the shape is driven by the graph's
// structure, not by spacing. The fix that actually applies is `orientToViewport` in
// StemmaCanvas: a force-directed layout has no meaningful axis, so it can simply be
// rotated to match the screen. Spacing is therefore left at the values measured good for
// the real book (ch40 default: zoom 0.745, all 20 names drawn).
export const colaOptions = (reducedMotion: boolean, nodeCount = 0): Record<string, unknown> => {
  const large = nodeCount > 40;
  const social = large ? 100 : 95;
  const identity = large ? 80 : 80;
  return {
    name: "cola",
    animate: true,
    infinite: false,
    maxSimulationTime: reducedMotion ? 800 : SETTLE_MS,
    nodeSpacing: large ? 28 : 22,
    // Small casts: labels count as part of the node for overlap avoidance (without it
    // Caelum × Sparrow overlapped on the 13-node demo). Large casts: node bodies only —
    // label-inclusive boxes made cola stack 70 nodes into a portrait column; the minor
    // labels are hidden there anyway (stemmaModel.isMinorLabel).
    nodeDimensionsIncludeLabels: !large,
    edgeLength: (e: { data(k: string): unknown }) => (e.data("kind") === "identity" ? identity : social),
    convergenceThreshold: 0.01,
    fit: false,
  };
};
