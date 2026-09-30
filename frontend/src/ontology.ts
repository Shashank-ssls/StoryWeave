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

// ---------------------------------------------------------------------------------
// R4's closed twelve-relation vocabulary (CLAUDE.md retrofit rule 3). These arrive on
// the wire in SCREAMING_SNAKE; the CamelCase map above is v1's and stays for the frozen
// Hollow Crown payload, which still carries the old names.
//
// R7 removes "linked" from the UI entirely: a reader shown "linked" learns nothing the
// dot positions did not already tell them. Every served relation therefore has a plain
// word here, and `tieLabel` humanises anything unexpected rather than falling back.

/** Forward reading, source -> target. Plain words, no jargon. */
export const R4_RELATION_LABELS: Record<string, string> = {
  KIN_OF: "family",
  ROMANTIC_WITH: "romantic with",
  ALLY_OF: "ally of",
  ENEMY_OF: "enemy of",
  SERVES: "serves",
  MENTOR_OF: "mentors",
  KILLED: "killed",
  SAME_AS: "same as",
  MEMBER_OF: "member of",
  LEADS: "leads",
  OWNS: "owns",
  LOCATED_IN: "in",
};

/** Reading the same edge backwards, target -> source. Only the directed ones differ. */
export const R4_RELATION_INVERSE: Record<string, string> = {
  SERVES: "commands",
  MENTOR_OF: "trained by",
  KILLED: "killed by",
  MEMBER_OF: "has member",
  LEADS: "led by",
  OWNS: "owned by",
  LOCATED_IN: "contains",
};

/**
 * Relations that get an arrowhead at the TARGET end. The symmetric ones deliberately do
 * not: an arrow on "ally of" invites the reader to infer a direction the book never
 * stated.
 *
 * This set mirrors the backend's own split exactly — `SYMMETRIC_R4_RELATIONS` in
 * `storyweave/db/models.py`, which is what `/ego` already serialises as its `directed`
 * flag (`api/app.py`). Of the closed twelve, four are symmetric (ALLY_OF, ENEMY_OF,
 * ROMANTIC_WITH, SAME_AS) and eight are directed. `KIN_OF` was missing here, so the
 * canvas drew a kinship tie with no arrowhead while the ego panel read the same tie as
 * directed — the two disagreed about the same edge.
 *
 * The arrow points SOURCE -> TARGET, which is the direction the forward label in
 * `R4_RELATION_LABELS` is written in: "A serves B" points at the master, "A mentors B"
 * points at the student. Reading an edge from the other end uses
 * `R4_RELATION_INVERSE`, and the arrow is what tells the reader which end they are on.
 *
 * KIN_OF is a deliberate half-measure and worth stating plainly: the edge is drawn with
 * an arrow because the backend calls it directed, but the stored `kin_role` ("sister",
 * "nephew") does NOT record WHICH endpoint holds the role — `_possessive_kin` in
 * `extract/validator.py` returns the kin noun alone, with no binding to a participant.
 * So the arrow shows the stored source -> target ordering and nothing more; it is not
 * evidence of a parent -> child direction, and no such direction is synthesised here.
 *
 * The lower block is v1's CamelCase vocabulary, which the frozen Hollow Crown demo
 * payload still carries (integration rule I2 — it must keep rendering unchanged). Only
 * the v1 names that map onto one of the eight directed relations are listed, so this is
 * the same rule expressed in the older names rather than a second, looser rule. Without
 * it the demo — the Landing mini graph and the Dossier ego graph, which is what a first
 * visitor actually sees — drew ZERO arrowheads, because not one of its relation names
 * appeared in the R4-only set above.
 */
export const DIRECTED_RELATIONS = new Set([
  // R4's closed twelve, minus the four symmetric ones.
  "KIN_OF", "SERVES", "MENTOR_OF", "KILLED", "MEMBER_OF", "LEADS", "OWNS", "LOCATED_IN",
  // v1 (Hollow Crown) names for the same eight relations.
  "LocatedIn", "MemberOf", "AffiliatedWith", "LeaderOf", "OwnsItem", "HasAbility",
  "HasTitle", "ParticipatedIn", "Serves", "Killed", "Mentor", "Student",
  "Parent", "Child",
]);

/**
 * The counterpart of the set above: relations that must NEVER carry an arrowhead.
 * Exported so the unit test can assert the two partition the closed vocabulary rather
 * than testing the implementation against itself.
 */
export const SYMMETRIC_RELATIONS = new Set([
  // R4's four.
  "ALLY_OF", "ENEMY_OF", "ROMANTIC_WITH", "SAME_AS",
  // v1 names with no direction to state.
  "Ally", "Enemy", "Rival", "Family", "Sibling", "Spouse", "Romantic", "RelatedTo",
]);
