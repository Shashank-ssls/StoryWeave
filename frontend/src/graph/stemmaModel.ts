// Stemma (full graph) view logic (DESIGN_SPEC §6.3, §7.5, §8.3) — pure functions over the
// R4 view model, unit-tested in stemmaModel.test.ts. The canvas component only draws what
// these return, so every rule about WHAT is visible lives here, not in Cytoscape code.

import type { ViewModel, VmEdge, VmNode } from "./viewModel";

/**
 * R7 removed everything that used to live here: `ShowFilter`, `SHOW_ALL`, `CastSize`,
 * `kindShown` and `visibleGraph`, which filtered the payload by node kind and by degree
 * before drawing it.
 *
 * That was a violation of retrofit rule 6 (the client renders what it receives) and the
 * reason defect D3 looked like a UI bug: the server sent the whole fenced cast at every
 * setting, and the rail's "Principal / Everyone" switch just hid rows of it locally, so
 * the payload never changed and the dial could not be measured from outside the browser.
 * The cast dial and the type overlays are now query parameters (`ChapterProvider.setView`)
 * and the SQL decides, where the fence can be read beside them.
 *
 * `folded` ("+N members") went too: it counted members the local filter had hidden, and
 * with no local filter there is nothing to count.
 */

export interface VisibleGraph {
  nodes: VmNode[];
  edges: VmEdge[];
}

/** Ids of nodes that touch an identity edge. Not a filter — the canvas styles them. */
export function identityEndpoints(vm: ViewModel): Set<string> {
  const out = new Set<string>();
  for (const e of vm.edges) if (e.kind === "identity") { out.add(e.source); out.add(e.target); }
  return out;
}

/** The payload, unfiltered. Kept as a named function so the canvas has one entry point
 *  and so `rendered === payload` is a property some code actually asserts. */
export function visibleGraph(vm: ViewModel): VisibleGraph {
  return { nodes: vm.nodes, edges: vm.edges };
}

/**
 * Cytoscape `data` for one edge, shared by EVERY canvas that uses `codexStyle`.
 *
 * The stylesheet maps `width: data(thickness)` and `target-arrow-shape: data(arrow)`.
 * The Landing mini graph and the Dossier ego graph each built their own edge data and
 * omitted both keys, so those mappers resolved to `undefined` and Cytoscape drew the
 * lines at arbitrary slab widths with no arrowheads (reported and reproduced: the thick
 * brown bars behind the Hollow Crown mini graph, and the beige spokes in the ego graph).
 * One builder means a missing key cannot happen again.
 *
 * `label` is passed in rather than derived here: the Stemma draws relation words on
 * every line (R7), while the two small panel graphs have no room for them.
 */
export function edgeData(e: VmEdge, label = ""): Record<string, unknown> {
  const thick = e.weight >= 5 ? 3 : e.weight >= 2 ? 2 : 1;
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    kind: e.kind,
    relation: e.relation,
    revealed_chapter: e.revealed_chapter,
    label,
    grade: e.grade ?? "STATED",
    arrow: e.directed ? "triangle" : "none",
    // Bucketed to 3 steps rather than mapped continuously, so a pair mentioned forty
    // times cannot draw a line so thick it reads as a different kind of relationship.
    thickness: thick,
    // Cytoscape sizes an arrowhead as `arrow-scale` x the edge WIDTH, so the old fixed
    // 0.8 drew a head smaller than the 1px line it sat on: present in the DOM, invisible
    // on screen. A fixed scale is the wrong shape of fix too — it makes a weight-1 tie's
    // head three times smaller than a weight-5 tie's, and weight-1 is most of the graph.
    // The scale therefore falls as the line thickens, which keeps the drawn head roughly
    // constant. [MEASURED] at the ch40 default fit (zoom 1.05, 1280x720): every one of
    // the 11 directed ties shows a head, and both ENEMY_OF ties show none.
    arrowScale: [3.2, 2.0, 1.6][thick - 1],
  };
}

/** §8.3 focus set: the focus node plus everything within `steps` hops over VISIBLE edges. */
export function focusSet(edges: VmEdge[], focusId: string, steps: number): Set<string> {
  const adj = new Map<string, Set<string>>();
  for (const e of edges) {
    (adj.get(e.source) ?? adj.set(e.source, new Set()).get(e.source)!).add(e.target);
    (adj.get(e.target) ?? adj.set(e.target, new Set()).get(e.target)!).add(e.source);
  }
  let frontier = new Set([focusId]);
  const out = new Set([focusId]);
  for (let s = 0; s < steps; s++) {
    const next = new Set<string>();
    for (const id of frontier) for (const nb of adj.get(id) ?? []) if (!out.has(nb)) { out.add(nb); next.add(nb); }
    frontier = next;
  }
  return out;
}

/** Neighbours of the focus node in a stable order (for arrow-key cycling, §8.3). */
export function neighboursOf(edges: VmEdge[], nodes: VmNode[], focusId: string): string[] {
  const set = focusSet(edges, focusId, 1);
  set.delete(focusId);
  const order = new Map(nodes.map((n, i) => [n.id, i]));
  return [...set].sort((a, b) => (order.get(a) ?? 0) - (order.get(b) ?? 0));
}

// §7.5 zoom tiers
export type ZoomTier = "far" | "default" | "close";
export function zoomTier(zoom: number): ZoomTier {
  if (zoom < 0.5) return "far";
  if (zoom > 1.5) return "close";
  return "default";
}

/**
 * §7.5 label rule. "Principal labels" at the default tier are not every label: above
 * LABEL_ALL_MAX visible nodes, minor nodes (degree < 3, no identity edge, not in the
 * focus set) wait for the close tier — measured at R5: labelling all 72 principal-cast
 * nodes of synthetic-100 at the default fit produced 40 overlapping labels.
 */
export const LABEL_ALL_MAX = 40;
/** How many "principal labels" a large cast shows at the default tier. */
export const LABEL_BUDGET = 22;

/**
 * Ids whose labels are MINOR (hidden at the default tier) for this visible set: empty for
 * casts up to LABEL_ALL_MAX; otherwise everything outside the budget, ranked identity
 * endpoints first, then degree, then first appearance (so the ranking is stable).
 */
export function labelRank(nodes: VmNode[], identityEndpoints: Set<string>): VmNode[] {
  return [...nodes].sort((a, b) => {
    const ai = identityEndpoints.has(a.id) ? 0 : 1;
    const bi = identityEndpoints.has(b.id) ? 0 : 1;
    return ai - bi || b.degree - a.degree || a.first_seen_chapter - b.first_seen_chapter || a.label.localeCompare(b.label);
  });
}

export function minorLabelIds(nodes: VmNode[], identityEndpoints: Set<string>): Set<string> {
  if (nodes.length <= LABEL_ALL_MAX) return new Set();
  return new Set(labelRank(nodes, identityEndpoints).slice(LABEL_BUDGET).map((n) => n.id));
}

export interface Box { x1: number; y1: number; x2: number; y2: number }

/**
 * Declutter (§7.2 "label collision"): walk labels in rank order and defer any label whose
 * box collides with an already-kept one. Deterministic, so zero overlaps at the default
 * fit hold by construction, not by luck of the physics. Returns the ids to defer.
 */
export function declutterLabels(ranked: { id: string; box: Box }[]): Set<string> {
  const kept: Box[] = [];
  const deferred = new Set<string>();
  for (const { id, box } of ranked) {
    const hit = kept.some((k) => Math.min(k.x2, box.x2) > Math.max(k.x1, box.x1) && Math.min(k.y2, box.y2) > Math.max(k.y1, box.y1));
    if (hit) deferred.add(id);
    else kept.push(box);
  }
  return deferred;
}

export function labelVisible(
  tier: ZoomTier,
  node: { isFocus: boolean; isIdentityEndpoint: boolean; isMinor?: boolean; inFocusSet?: boolean },
): boolean {
  if (tier === "far") return node.isFocus || node.isIdentityEndpoint;
  if (tier === "close") return true;
  return !node.isMinor || node.isFocus || Boolean(node.inFocusSet);
}

/** §6.3 item 2 — search over the FENCED payload's node labels only (every alias is its own
 *  node per the R0 D4 verdict). Case-insensitive substring; exact-prefix matches first. */
export function searchNames(vm: ViewModel, query: string): VmNode[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const hits = vm.nodes.filter((n) => n.label.toLowerCase().includes(q));
  return hits.sort((a, b) => {
    const ap = a.label.toLowerCase().startsWith(q) ? 0 : 1;
    const bp = b.label.toLowerCase().startsWith(q) ? 0 : 1;
    return ap - bp || b.degree - a.degree || a.label.localeCompare(b.label);
  });
}

/** Person node size (§7.1): clamp(16, 12 + 3·√degree, 34); others fixed. */
export function nodeSize(n: VmNode): number {
  if (n.kind === "thing") return 20;
  if (n.kind !== "person") return 16;
  return Math.max(16, Math.min(34, 12 + 3 * Math.sqrt(n.degree)));
}
