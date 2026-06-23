// The 8-type ontology (SPEC §5.1) and its visual vocabulary. One muted, harmonious
// hue per type — same lightness/chroma in oklch, hue is the only variable, so the
// legend reads as a family rather than a box of crayons. Order is the SPEC order.

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

export const TYPE_COLOR: Record<NodeTypeName, string> = {
  Character: "oklch(0.80 0.11 85)", // amber — the people
  Place: "oklch(0.78 0.09 150)", // green
  Organization: "oklch(0.72 0.12 25)", // crimson
  Item: "oklch(0.80 0.09 195)", // teal
  Ability: "oklch(0.76 0.11 300)", // violet
  Concept: "oklch(0.78 0.10 250)", // blue
  Event: "oklch(0.79 0.11 60)", // ochre
  Title: "oklch(0.78 0.10 350)", // rose
};

export function typeColor(type: string): string {
  return (TYPE_COLOR as Record<string, string>)[type] ?? "oklch(0.70 0 0)";
}

// Tier-3 identity relations get the bloom treatment — the reveal made visible.
export const IDENTITY_RELATIONS = new Set([
  "SAME_AS",
  "ALIAS",
  "SECRET_IDENTITY",
  "REINCARNATION",
  "TRANSMIGRATED_INTO",
]);
