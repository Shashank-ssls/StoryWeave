// The 8-type ontology (SPEC §5.1) + the design-system palette. HEX only — Cytoscape's
// canvas renderer does not parse oklch(), which is exactly why the old build rendered
// every node grey. The legend and the graph both read from TYPE_COLOR, so they cannot
// disagree. See frontend/DESIGN.md for the rationale.

// The committed CC0 demo — protected from deletion (the build depends on it).
export const DEMO_SLUG = "the-hollow-crown";

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

// Curated human-readable edge labels. A relation is only labelled in the graph if it is
// in this map; anything else (the generic `RelatedTo` fallback, or any stray/garbage
// relation) is treated as LOW-QUALITY and its label is HIDDEN — the edge still draws, it
// just carries no noisy text. `RelatedTo` is deliberately omitted: it means only "these
// co-occur", carries no relation, and dominates the graph (~170 edges), so showing "related
// to" everywhere is clutter, not information.
export const RELATION_LABELS: Record<string, string> = {
  // Tier 1 — structural
  AffiliatedWith: "affiliated with",
  LocatedIn: "in",
  MemberOf: "member of",
  LeaderOf: "leads",
  HasAbility: "has ability",
  OwnsItem: "owns",
  HasTitle: "holds",
  ParticipatedIn: "took part in",
  // (RelatedTo intentionally omitted -> label hidden)
  // Tier 2 — social
  Ally: "ally of",
  Enemy: "enemy of",
  Rival: "rival of",
  Mentor: "mentor of",
  Student: "student of",
  Family: "family of",
  Parent: "parent of",
  Child: "child of",
  Sibling: "sibling of",
  Spouse: "spouse of",
  Romantic: "romantic with",
  Betrayed: "betrayed",
  Serves: "serves",
  Killed: "killed",
  Protects: "protects",
  Fears: "fears",
  Respects: "respects",
  // Tier 3 — identity (always meaningful, always labelled)
  SAME_AS: "same as",
  ALIAS: "alias",
  SECRET_IDENTITY: "secret identity",
  REINCARNATION: "reincarnation of",
  TRANSMIGRATED_INTO: "transmigrated into",
};

// Graph/hover label: the curated label, or "" for low-quality/unknown relations (hidden).
export function relationLabel(relation: string): string {
  return RELATION_LABELS[relation] ?? "";
}

// Path/connection label: like relationLabel but never empty — in a traced path or a
// connections list you always want to name the hop, so a hidden relation reads "linked".
export function relationStepLabel(relation: string): string {
  return RELATION_LABELS[relation] ?? "linked";
}
