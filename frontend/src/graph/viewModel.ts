// Graph view model (FRONTEND_OVERHAUL.md §6; DESIGN_SPEC §7.1, §7.3, §7.4, §8.4).
// A PURE function from a fenced payload to what the canvas / dossier may draw. This is
// where the UI's share of the fence and the citation gate lives, so it is tested like
// data code (see viewModel.test.ts), not UI code. Built at R4 for the Dossier's ego
// graph, ties and cast list; R5's Stemma extends it (principal filter, focus sets).
//
// Field names are the real wire names from the R0 recon (`evidence_span`,
// `revealed_chapter`, `first_seen_chapter`, `tier`, `relation`).

import type { GraphEdgeData, GraphElements, GraphNodeData } from "../types";
import { IDENTITY_RELATIONS, RELATION_LABELS } from "../ontology";

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

/** Short lowercase label for a social/structural tie ("ally of", "in"); unknown → "linked". */
export function tieLabel(relation: string): string {
  if (IDENTITY_RELATIONS.has(relation)) return IDENTITY_COPY[relation]?.short ?? "identity";
  return RELATION_LABELS[relation] ?? "linked";
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
      });
      continue;
    }
    existing.relations.push(data.relation);
    if (kind === "identity" && existing.kind !== "identity") {
      // identity absorbs: it becomes the edge's face, direction and quote
      existing.id = data.id;
      existing.source = data.source;
      existing.target = data.target;
      existing.kind = "identity";
      existing.relation = data.relation;
      existing.revealed_chapter = data.revealed_chapter;
      existing.first_seen_chapter = data.first_seen_chapter;
      existing.evidence_span = data.evidence_span;
    } else if (existing.kind !== "identity") {
      existing.revealed_chapter = Math.min(existing.revealed_chapter, data.revealed_chapter);
      existing.first_seen_chapter = Math.min(existing.first_seen_chapter, data.first_seen_chapter);
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
