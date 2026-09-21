// Pure diff between two fenced graph payloads (FRONTEND_OVERHAUL.md §6; DESIGN_SPEC §8.1
// step 3). Drives the forward-move toast now (R3) and the reveal moment later (R6), and
// the Dossier's "changed" tags (R4, spec F8: both inputs are fenced payloads, nothing
// else is ever consulted).
//
// `prev` may be null (no earlier payload — e.g. the first load, or a jump from a chapter
// whose payload was purged): then everything in `next` counts as new.

import type { GraphEdgeData, GraphElements, GraphNodeData } from "../types";
import { IDENTITY_RELATIONS } from "../ontology";

export interface GraphDiff {
  newNodes: GraphNodeData[];
  newEdges: GraphEdgeData[];
  /** Subset of `newEdges` whose relation is an identity relation (SAME_AS, ALIAS, ...). */
  newIdentityEdges: GraphEdgeData[];
}

export function isIdentityRelation(relation: string): boolean {
  return IDENTITY_RELATIONS.has(relation);
}

export function diffGraphs(prev: GraphElements | null, next: GraphElements): GraphDiff {
  const prevNodeIds = new Set(prev?.nodes.map((n) => n.data.id) ?? []);
  const prevEdgeIds = new Set(prev?.edges.map((e) => e.data.id) ?? []);

  const newNodes = next.nodes.map((n) => n.data).filter((n) => !prevNodeIds.has(n.id));
  const newEdges = next.edges.map((e) => e.data).filter((e) => !prevEdgeIds.has(e.id));
  const newIdentityEdges = newEdges.filter((e) => isIdentityRelation(e.relation));

  return { newNodes, newEdges, newIdentityEdges };
}
