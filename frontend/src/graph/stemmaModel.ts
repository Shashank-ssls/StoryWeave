// Stemma (full graph) view logic (DESIGN_SPEC §6.3, §7.5, §8.3) — pure functions over the
// R4 view model, unit-tested in stemmaModel.test.ts. The canvas component only draws what
// these return, so every rule about WHAT is visible lives here, not in Cytoscape code.

import type { NodeKind, ViewModel, VmEdge, VmNode } from "./viewModel";

export interface ShowFilter {
  people: boolean;
  orders: boolean;
  places: boolean; // places + things ("Places & Relics")
}
export const SHOW_ALL: ShowFilter = { people: true, orders: true, places: true };

export type CastSize = "principal" | "everyone";

export interface VisibleGraph {
  nodes: VmNode[];
  edges: VmEdge[];
  /** Organization id → number of hidden members folded into it (fenced payload only). */
  folded: Map<string, number>;
}

function kindShown(kind: NodeKind, show: ShowFilter): boolean {
  if (kind === "person") return show.people;
  if (kind === "order") return show.orders;
  return show.places;
}

const MEMBERSHIP = new Set(["MemberOf", "AffiliatedWith", "LeaderOf"]);

/** Ids of nodes that touch an identity edge. */
export function identityEndpoints(vm: ViewModel): Set<string> {
  const out = new Set<string>();
  for (const e of vm.edges) if (e.kind === "identity") { out.add(e.source); out.add(e.target); }
  return out;
}

/**
 * §6.3 item 4 — Principal = degree ≥ 2 OR any identity edge OR is the focus. Hidden
 * organisation members fold into their organisation as a "+N" count. N counts ONLY
 * members present in the fenced payload (nothing beyond the bookmark exists client-side),
 * so the badge is a count of what the reader has already met, not of the future — F2 holds.
 */
export function visibleGraph(vm: ViewModel, opts: { show: ShowFilter; cast: CastSize; focusId: string | null }): VisibleGraph {
  const ids = identityEndpoints(vm);
  const visible = new Set<string>();
  for (const n of vm.nodes) {
    if (!kindShown(n.kind, opts.show)) continue;
    if (opts.cast === "everyone" || n.degree >= 2 || ids.has(n.id) || n.id === opts.focusId) visible.add(n.id);
  }
  const folded = new Map<string, number>();
  if (opts.cast === "principal") {
    for (const e of vm.edges) {
      if (!MEMBERSHIP.has(e.relation)) continue;
      // member → org: the org is whichever endpoint is an order
      const src = vm.byId.get(e.source);
      const tgt = vm.byId.get(e.target);
      if (!src || !tgt) continue;
      const [member, org] = tgt.kind === "order" ? [src, tgt] : src.kind === "order" ? [tgt, src] : [null, null];
      if (!member || !org) continue;
      if (visible.has(org.id) && !visible.has(member.id) && kindShown(member.kind, opts.show)) {
        folded.set(org.id, (folded.get(org.id) ?? 0) + 1);
      }
    }
  }
  return {
    nodes: vm.nodes.filter((n) => visible.has(n.id)),
    edges: vm.edges.filter((e) => visible.has(e.source) && visible.has(e.target)),
    folded,
  };
}

/** §8.3 focus set: the focus node plus everything within `steps` hops over VISIBLE edges. */
export function focusSet(edges: VmEdge[], focusId: string, steps: 1 | 2): Set<string> {
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
