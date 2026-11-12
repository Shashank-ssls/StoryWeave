// Pure diff between two fenced graph payloads (FRONTEND_OVERHAUL.md §6; DESIGN_SPEC §8.1
// step 3). Drives the forward-move toast (R3), the Dossier's "changed" tags (R4, spec F8),
// and the reveal moment (R6, spec §8.2).
//
// `prev` may be null (no earlier payload — e.g. the first load, or a jump from a chapter
// whose payload was purged): then everything in `next` counts as new, and no identity edge
// can ever be classified as deepening (there is nothing to deepen from).
//
// R6 identity diffing (RESOLVED design decision — FRONTEND_OVERHAUL.md §9 "Open questions
// for R6"): reveals are keyed by the UNORDERED ENTITY PAIR, not the edge id, because the
// backend may reissue an identity edge under a new id + new relation for the same two
// entities (verified live: Wren/Caelum's SECRET_IDENTITY `e12` at chapter 2 is replaced by
// TRANSMIGRATED_INTO `e14` at chapter 4 — same pair, `e12` simply absent from n=4). A naive
// id-based diff would report `e14` as a brand-new identity edge and re-play the chapter-2
// reveal; pair-keyed diffing instead recognises it as a deepening of what the reader already
// knows.
//   - pair has no identity edge in `prev`, has one in `next` -> a NORMAL reveal.
//   - pair has an identity edge in both, with a DIFFERENT relation -> a DEEPENING reveal.
//   - pair has an identity edge in both, with the SAME relation (even if the edge id
//     changed) -> no reveal — nothing new to tell the reader.

import type { GraphEdgeData, GraphElements, GraphNodeData } from "../types";
import { IDENTITY_RELATIONS } from "../ontology";

export type RevealKind = "normal" | "deepen";

export interface Reveal {
  kind: RevealKind;
  /** The two entity ids, sorted — the diffing key, not display order. */
  pair: [string, string];
  /** The edge as it stands at the NEW chapter. Its own source/target carry sentence direction. */
  edge: GraphEdgeData;
  /** Only set for `kind: "deepen"` — the same pair's identity edge at the OLD chapter. */
  previousEdge?: GraphEdgeData;
}

export interface GraphDiff {
  newNodes: GraphNodeData[];
  newEdges: GraphEdgeData[];
  reveals: Reveal[];
}

export function isIdentityRelation(relation: string): boolean {
  return IDENTITY_RELATIONS.has(relation);
}

// P5 / §8.4: "no quote, no edge" — the same citation-gate rule `graph/viewModel.ts` applies
// when drawing the Stemma/ego graph applies here too. A quote-less identity edge is never
// shown anywhere in the UI, so it must never drive (or count as prior state for) a reveal —
// otherwise the overlay could either announce a claim with no evidence, or treat a pair the
// reader never actually saw joined as already-known when a real, quoted edge arrives later.
function hasQuote(e: GraphEdgeData): boolean {
  return typeof e.evidence_span === "string" && e.evidence_span.trim().length > 0;
}

function isRevealable(e: GraphEdgeData): boolean {
  return isIdentityRelation(e.relation) && hasQuote(e);
}

function pairKey(a: string, b: string): string {
  return a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`;
}

function sortedPair(a: string, b: string): [string, string] {
  return a < b ? [a, b] : [b, a];
}

/** The identity edge that represents each pair: the latest-revealed one, ties broken by
 *  id. R7: a pair can legitimately carry several (the demo's layered Wren/Caelum reveal),
 *  so "last one in payload order" would make the prior state depend on row order. */
function identityByPair(payload: GraphElements | null | undefined): Map<string, GraphEdgeData> {
  const map = new Map<string, GraphEdgeData>();
  for (const { data } of payload?.edges ?? []) {
    if (!isRevealable(data)) continue;
    const key = pairKey(data.source, data.target);
    const held = map.get(key);
    if (
      !held ||
      data.revealed_chapter > held.revealed_chapter ||
      (data.revealed_chapter === held.revealed_chapter && data.id > held.id)
    ) {
      map.set(key, data);
    }
  }
  return map;
}

/** Classifies a single identity edge against an (optionally cached) earlier payload — the
 *  same rule `diffGraphs` applies per new edge, exposed standalone for Dossier replay
 *  (R6 spec §8.2: "no network needed" — the caller passes whatever is already in the
 *  chapter model's cache, or null if that earlier chapter was never fetched). Returns null
 *  only when the pair's relation is literally unchanged (nothing to show as a reveal). */
export function classifyReveal(prevPayload: GraphElements | null, edge: GraphEdgeData): Reveal | null {
  if (!isRevealable(edge)) return null;
  const prevEdge = identityByPair(prevPayload).get(pairKey(edge.source, edge.target));
  const pair = sortedPair(edge.source, edge.target);
  if (!prevEdge) return { kind: "normal", pair, edge };
  if (prevEdge.relation !== edge.relation) return { kind: "deepen", pair, edge, previousEdge: prevEdge };
  return null;
}

export function diffGraphs(prev: GraphElements | null, next: GraphElements): GraphDiff {
  const prevNodeIds = new Set(prev?.nodes.map((n) => n.data.id) ?? []);
  const prevEdgeIds = new Set(prev?.edges.map((e) => e.data.id) ?? []);

  const newNodes = next.nodes.map((n) => n.data).filter((n) => !prevNodeIds.has(n.id));
  const newEdges = next.edges.map((e) => e.data).filter((e) => !prevEdgeIds.has(e.id));

  const prevByPair = identityByPair(prev);

  // R7: one reveal per PAIR, even when several new identity edges arrive for it at once.
  //
  // The header above keys reveals by pair, but only the LOOKUP was keyed that way — the
  // output was one reveal per new edge. That was invisible while the payload carried at
  // most one identity edge per pair, which is what the R0 fixtures captured. R4's D1 fix
  // (build the payload from rows instead of an `nx.DiGraph`, which was collapsing
  // parallel edges) means both now arrive, exactly as the demo seeds them: Wren/Caelum is
  // SECRET_IDENTITY@2 *and* TRANSMIGRATED_INTO@4. Jumping 1→4 therefore produced two
  // "normal" reveals for one pair and a pager reading "1 of 3" instead of "1 of 2".
  //
  // The winner is the latest-revealed edge — the same "later reveal is the current truth"
  // rule `viewModel.ts` uses to decide which identity a merged line shows.
  const newestByPair = new Map<string, GraphEdgeData>();
  for (const edge of newEdges) {
    if (!isRevealable(edge)) continue;
    const key = pairKey(edge.source, edge.target);
    const held = newestByPair.get(key);
    if (
      !held ||
      edge.revealed_chapter > held.revealed_chapter ||
      (edge.revealed_chapter === held.revealed_chapter && edge.id > held.id)
    ) {
      newestByPair.set(key, edge);
    }
  }

  const reveals: Reveal[] = [];
  for (const [key, edge] of newestByPair) {
    const prevEdge = prevByPair.get(key);
    const pair = sortedPair(edge.source, edge.target);
    if (!prevEdge) reveals.push({ kind: "normal", pair, edge });
    else if (prevEdge.relation !== edge.relation) reveals.push({ kind: "deepen", pair, edge, previousEdge: prevEdge });
    // same relation, whatever the id: nothing to reveal
  }
  reveals.sort(
    (a, b) => a.edge.revealed_chapter - b.edge.revealed_chapter || pairKey(...a.pair).localeCompare(pairKey(...b.pair)),
  );

  return { newNodes, newEdges, reveals };
}
