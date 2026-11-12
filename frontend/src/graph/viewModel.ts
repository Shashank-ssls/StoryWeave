// Graph view model (FRONTEND_OVERHAUL.md §6; DESIGN_SPEC §7.1, §7.3, §7.4, §8.4).
// A PURE function from a fenced payload to what the canvas / dossier may draw. This is
// where the UI's share of the fence and the citation gate lives, so it is tested like
// data code (see viewModel.test.ts), not UI code. Built at R4 for the Dossier's ego
// graph, ties and cast list; R5's Stemma extends it (principal filter, focus sets).
//
// Field names are the real wire names from the R0 recon (`evidence_span`,
// `revealed_chapter`, `first_seen_chapter`, `tier`, `relation`).

import type { GraphEdgeData, GraphElements, GraphNodeData } from "../types";
import {
  DIRECTED_RELATIONS,
  IDENTITY_RELATIONS,
  R4_RELATION_INVERSE,
  R4_RELATION_LABELS,
  RELATION_LABELS,
} from "../ontology";

export type NodeKind = "person" | "order" | "place" | "thing";
export type EdgeKind = "social" | "structural" | "identity";

export interface VmNode {
  id: string;
  label: string;
  kind: NodeKind;
  /** Node count of merged edges touching this node (from the fenced payload only). */
  degree: number;
  initial: string;
  first_seen_chapter: number;
  revealed_chapter: number;
  raw: GraphNodeData;
}

export interface VmEdge {
  id: string;
  source: string;
  target: string;
  kind: EdgeKind;
  /** The primary relation (the identity relation when one absorbed a social edge). */
  relation: string;
  /** Every relation merged into this edge, in payload order. */
  relations: string[];
  revealed_chapter: number;
  first_seen_chapter: number;
  evidence_span: string | null;
  /** R7: "STATED" draws solid, "INFERRED" draws dashed and reads "(implied)". A pre-R4
   *  payload has no grade at all; those draw solid, as they always did. */
  grade: string | null;
  /** The verbatim sentence (rule 4). Falls back to `evidence_span` for pre-R4 rows. */
  quote: string | null;
  quoteChapter: number | null;
  /** How many times the extractor saw this tie; drives line width in 3 steps. */
  weight: number;
  /** Arrowheads only on directed relations. */
  directed: boolean;
}

export interface ViewModel {
  nodes: VmNode[];
  edges: VmEdge[];
  /** Concept / Event nodes: not drawn, listed in the Dossier as "Also mentioned" (§7.1). */
  alsoMentioned: GraphNodeData[];
  byId: Map<string, VmNode>;
}

export interface ViewModelOptions {
  /** Where the missing-quote warning goes; defaults to console.warn (§8.4). Tests inject. */
  warn?: (message: string) => void;
}

// §7.1 kind mapping. Title → null (never a node); Concept/Event → null here, they go to
// `alsoMentioned` instead. Species/Rank are subtypes, not types, so they never arrive here.
export function kindOf(type: string): NodeKind | null {
  switch (type) {
    case "Character":
      return "person";
    case "Organization":
      return "order";
    case "Place":
      return "place";
    case "Item":
    case "Ability":
      return "thing";
    default:
      return null;
  }
}

// Tier-1 relations that draw as the dashed structural line (§7.3 "member-of, located-in").
const STRUCTURAL = new Set(["LocatedIn", "MemberOf", "AffiliatedWith", "LeaderOf"]);

export function edgeKindOf(relation: string): EdgeKind {
  if (IDENTITY_RELATIONS.has(relation)) return "identity";
  if (STRUCTURAL.has(relation)) return "structural";
  return "social";
}

// §7.4 relation copy. Sentences are `{a}`/`{b}` templates in source→target order (the
// line has no arrowhead; direction lives in the copy). Every identity enum in
// ontology.ts's IDENTITY_RELATIONS has a row — SAME_AS shares ALIAS's pattern per the
// spec table; no enum was missing, so nothing had to be added.
export interface IdentityCopy {
  sentence: string;
  kicker: string;
  short: string;
}
export const IDENTITY_COPY: Record<string, IdentityCopy> = {
  SECRET_IDENTITY: { sentence: "{a} is {b}.", kicker: "Secret identity", short: "secret identity" },
  ALIAS: { sentence: "{a} is {b}.", kicker: "Alias", short: "alias" },
  SAME_AS: { sentence: "{a} is {b}.", kicker: "Alias", short: "alias" },
  REINCARNATION: { sentence: "{a} is {b} reborn.", kicker: "Reincarnation", short: "reincarnation" },
  TRANSMIGRATED_INTO: { sentence: "{a} now lives on as {b}.", kicker: "Transmigration", short: "transmigration" },
};

/**
 * Short lowercase label for a tie, in plain words.
 *
 * R7 removes the old `?? "linked"` fallback. "Linked" told the reader nothing the line
 * itself had not already said, and it was not a rare edge case: R4 replaced v1's
 * CamelCase vocabulary with R4's SCREAMING_SNAKE one, so after R5 EVERY new relation
 * missed `RELATION_LABELS` and every label in the graph read "linked". An unrecognised
 * relation is now humanised (`MENTOR_OF` -> "mentor of") rather than erased, which is
 * wrong-looking if we ever ship a relation we forgot to name — and visibly so, which is
 * the point.
 *
 * `backwards` reads a directed edge from the target's side ("serves" -> "commands").
 */
export function tieLabel(relation: string, backwards = false): string {
  if (UNLABELLED.has(relation)) return "";
  if (backwards) {
    const inverse = R4_RELATION_INVERSE[relation];
    if (inverse) return inverse;
  }
  if (IDENTITY_RELATIONS.has(relation)) return IDENTITY_COPY[relation]?.short ?? "identity";
  return R4_RELATION_LABELS[relation] ?? RELATION_LABELS[relation] ?? humanise(relation);
}

/**
 * The one relation that stays wordless. `RelatedTo` is v1's co-occurrence rule: it means
 * only "these two names appeared near each other", which is not a relationship, and R1
 * [MEASURED] it producing 160 of v1's 162 false positives. Retrofit rule 5 keeps it out
 * of the default graph entirely; it survives only in the frozen Hollow Crown demo, where
 * labelling ~170 lines "related to" would be clutter rather than information. Naming it
 * here is deliberate: the empty label is a decision, not a lookup that quietly missed.
 */
const UNLABELLED = new Set(["RelatedTo"]);

/** Last resort: `MENTOR_OF` -> "mentor of", `AffiliatedWith` -> "affiliated with". */
export function humanise(relation: string): string {
  return relation
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .trim();
}

/**
 * R7: the label a reader sees on the line.
 *
 * §7.3 merges parallel edges into ONE line per pair, so a line can stand for several
 * relations. v1 labelled such a line with the primary relation alone, which silently
 * hid the rest: at chapter 40 the Rule Zero capture found 18 payload edges drawn as 13
 * lines, so five relations had no words anywhere on screen. Every merged relation is
 * therefore named here, and the "(implied)" suffix applies to the line as a whole.
 */
export function edgeLabel(edge: VmEdge, backwards = false): string {
  const seen = new Set<string>();
  for (const r of edge.relations) {
    const label = tieLabel(r, backwards);
    if (label) seen.add(label);
  }
  const base = [...seen].join(" · ") || tieLabel(edge.relation, backwards);
  return edge.grade === "INFERRED" ? `${base} (implied)` : base;
}

function pairKey(a: string, b: string): string {
  return a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`;
}

export function buildViewModel(payload: GraphElements, options: ViewModelOptions = {}): ViewModel {
  const warn = options.warn ?? ((m: string) => console.warn(m));

  const nodes: VmNode[] = [];
  const alsoMentioned: GraphNodeData[] = [];
  const byId = new Map<string, VmNode>();

  for (const { data } of payload.nodes) {
    if (data.type === "Concept" || data.type === "Event") {
      alsoMentioned.push(data);
      continue;
    }
    const kind = kindOf(data.type);
    if (!kind) continue; // Title (and anything unknown): never a node
    const node: VmNode = {
      id: data.id,
      label: data.label,
      kind,
      degree: 0,
      initial: initialOf(data.label),
      first_seen_chapter: data.first_seen_chapter,
      revealed_chapter: data.revealed_chapter,
      raw: data,
    };
    nodes.push(node);
    byId.set(node.id, node);
  }

  // §7.3 parallel-edge merge, keyed on the unordered pair. An identity edge absorbs any
  // social/structural edge between the same two nodes; other parallels collapse to one
  // edge carrying the relation list. §8.4: an identity edge with no evidence_span is
  // dropped with a warning — the UI enforces the citation gate too.
  const merged = new Map<string, VmEdge>();
  for (const { data } of payload.edges) {
    if (!byId.has(data.source) || !byId.has(data.target)) continue; // endpoint not drawn
    const kind = edgeKindOf(data.relation);
    if (kind === "identity" && !hasQuote(data)) {
      warn(`viewModel: dropped identity edge ${data.id} (${data.relation}) — no evidence_span (§8.4)`);
      continue;
    }
    const key = pairKey(data.source, data.target);
    const existing = merged.get(key);
    if (!existing) {
      merged.set(key, {
        id: data.id,
        source: data.source,
        target: data.target,
        kind,
        relation: data.relation,
        relations: [data.relation],
        revealed_chapter: data.revealed_chapter,
        first_seen_chapter: data.first_seen_chapter,
        evidence_span: data.evidence_span,
        grade: data.grade ?? null,
        quote: data.quote ?? data.evidence_span,
        quoteChapter: data.quote_chapter ?? null,
        weight: data.weight ?? 1,
        directed: DIRECTED_RELATIONS.has(data.relation),
      });
      continue;
    }
    existing.relations.push(data.relation);
    // Which identity is CURRENT must not depend on payload row order. Wren-Caelum is
    // SECRET_IDENTITY at chapter 2 and TRANSMIGRATED_INTO at chapter 4; the line should
    // read as the later, deeper reveal. Both this merge and the specs' independent
    // oracle used to take whichever identity edge arrived first, which R7 exposed by
    // changing the payload query: the same pair started rendering as e12 rather than
    // e14. The later reveal now wins explicitly (ties broken by id, so it is total).
    const supersedes =
      kind === "identity" &&
      (existing.kind !== "identity" ||
        data.revealed_chapter > existing.revealed_chapter ||
        (data.revealed_chapter === existing.revealed_chapter && data.id > existing.id));
    if (supersedes) {
      // identity absorbs: it becomes the edge's face, direction and quote
      existing.id = data.id;
      existing.source = data.source;
      existing.target = data.target;
      existing.kind = "identity";
      existing.relation = data.relation;
      existing.revealed_chapter = data.revealed_chapter;
      existing.first_seen_chapter = data.first_seen_chapter;
      existing.evidence_span = data.evidence_span;
      existing.grade = data.grade ?? null;
      existing.quote = data.quote ?? data.evidence_span;
      existing.quoteChapter = data.quote_chapter ?? null;
      existing.directed = DIRECTED_RELATIONS.has(data.relation);
    } else if (existing.kind !== "identity") {
      existing.revealed_chapter = Math.min(existing.revealed_chapter, data.revealed_chapter);
      existing.first_seen_chapter = Math.min(existing.first_seen_chapter, data.first_seen_chapter);
      // Merged parallels: weight adds up (it drives line width), and the merged line
      // takes the WEAKEST grade of what it merged. One line now speaks for several
      // relations, so drawing it solid because one of them was STATED would let the
      // strong evidence vouch for the weak. Understating is the safe direction: the side
      // panel's ego list still grades each relation exactly, one row at a time.
      existing.weight += data.weight ?? 1;
      if (data.grade === "INFERRED") existing.grade = "INFERRED";
    }
  }

  const edges = [...merged.values()];
  for (const e of edges) {
    byId.get(e.source)!.degree += 1;
    byId.get(e.target)!.degree += 1;
  }

  return { nodes, edges, alsoMentioned, byId };
}

function hasQuote(e: GraphEdgeData): boolean {
  return typeof e.evidence_span === "string" && e.evidence_span.trim().length > 0;
}

// "the Gray Sparrow" → "G": skip a leading article so the focus disk shows a real initial.
export function initialOf(label: string): string {
  const words = label.trim().split(/\s+/);
  const first = words.length > 1 && /^(the|a|an)$/i.test(words[0] ?? "") ? words[1] : words[0];
  return (first ?? "?").charAt(0).toUpperCase();
}

/** Edges touching `id`, with the other endpoint resolved. */
export function tiesOf(vm: ViewModel, id: string): { edge: VmEdge; other: VmNode }[] {
  const out: { edge: VmEdge; other: VmNode }[] = [];
  for (const edge of vm.edges) {
    const otherId = edge.source === id ? edge.target : edge.target === id ? edge.source : null;
    if (otherId === null) continue;
    const other = vm.byId.get(otherId);
    if (other) out.push({ edge, other });
  }
  return out;
}

/** §6.2 cast order: degree descending, then first appearance, then label (stable). */
export function sortCast(nodes: VmNode[]): VmNode[] {
  return [...nodes].sort(
    (a, b) =>
      b.degree - a.degree ||
      a.first_seen_chapter - b.first_seen_chapter ||
      a.label.localeCompare(b.label),
  );
}

/** The principal character: highest-degree person at this chapter (P1). */
export function principalOf(vm: ViewModel): VmNode | null {
  const people = sortCast(vm.nodes.filter((n) => n.kind === "person"));
  return people[0] ?? null;
}

const WORDS = [
  "no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
  "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
  "eighteen", "nineteen", "twenty",
];
/** Lede count: words up to twenty, digits above (§6.2 item 3). */
export function countWords(k: number): string {
  if (!Number.isInteger(k) || k < 0) return String(k);
  return k <= 20 ? (WORDS[k] ?? String(k)) : String(k);
}
