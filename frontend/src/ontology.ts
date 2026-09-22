// Shared ontology constants used across the Codex UI. The 8-type node palette and the
// old Cytoscape hex-color constants this file used to hold were deleted at R9 step 8
// along with the legacy app (`GraphView.tsx`) that was their only reader — the new
// Stemma's Cytoscape style lives in `graph/codexStyle.ts` instead.

// The committed CC0 demo — protected from deletion (the build depends on it).
export const DEMO_SLUG = "the-hollow-crown";

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
