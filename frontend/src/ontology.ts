// The 8-type ontology (SPEC §5.1) + the design-system palette. HEX only — Cytoscape's
// canvas renderer does not parse oklch(), which is exactly why the old build rendered
// every node grey. The legend and the graph both read from TYPE_COLOR, so they cannot
// disagree. See frontend/DESIGN.md for the rationale.

export const NODE_TYPES = [
  "Character",
  "Place",
  "Organization",
  "Item",
  "Ability",
  "Concept",
  "Event",
  "Title",
] as const;

export type NodeTypeName = (typeof NODE_TYPES)[number];

// The constellation: distinct hues, harmonized luminance, legible on midnight.
export const TYPE_COLOR: Record<NodeTypeName, string> = {
  Character: "#7aa2f7",
  Place: "#63d29a",
  Organization: "#e36873",
  Item: "#d8a24a",
  Ability: "#b58cf0",
  Concept: "#46c7d8",
  Event: "#ee8b49",
  Title: "#de85c2",
};

export function typeColor(type: string): string {
  return (TYPE_COLOR as Record<string, string>)[type] ?? "#9aa0b4";
}

// Reserved gold — the reveal/identity accent and the bloom. Semantic, never decorative.
export const REVEAL = "#ffd073";
export const GROUND = "#0b0d14";
export const INK = "#e9e4d6";
export const INK_DIM = "#8b91a8";
export const EDGE_QUIET = "#39405c";

// Tier-3 identity relations get the bloom treatment — the reveal made visible.
export const IDENTITY_RELATIONS = new Set([
  "SAME_AS",
  "ALIAS",
  "SECRET_IDENTITY",
  "REINCARNATION",
  "TRANSMIGRATED_INTO",
]);

// Human-readable edge labels (shown on hover/select): "OwnsItem" -> "owns item",
// "SECRET_IDENTITY" -> "secret identity".
export function relationLabel(relation: string): string {
  return relation
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase();
}
