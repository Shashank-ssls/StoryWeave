import { describe, expect, it } from "vitest";
import { buildViewModel, kindOf } from "./viewModel";
import { declutterLabels, focusSet, LABEL_BUDGET, labelVisible, minorLabelIds, neighboursOf, nodeSize, searchNames, visibleGraph, zoomTier } from "./stemmaModel";
import type { GraphElements } from "../types";
import raw1 from "../../tests/fixtures/hollow-crown/graph-n1.json";
import raw3 from "../../tests/fixtures/hollow-crown/graph-n3.json";
import raw4 from "../../tests/fixtures/hollow-crown/graph-n4.json";

const g = (p: unknown): GraphElements => (p as { elements: GraphElements }).elements;

function node(id: string, type: string, label = id, first = 1) {
  return { data: { id, label, type, subtype: null, importance: 1, first_seen_chapter: first, revealed_chapter: first, extraction_method: "gliner", evidence_span: null, properties: {} } };
}
function edge(id: string, source: string, target: string, relation: string, quote: string | null = "q", rev = 1) {
  return { data: { id, source, target, relation, tier: 1, first_seen_chapter: rev, revealed_chapter: rev, extraction_method: "gliner", evidence_span: quote } };
}

// An org with 3 members: one hub (degree 2), two leaves (degree 1) → leaves fold.
const orgWorld = buildViewModel({
  nodes: [node("hub", "Character"), node("leaf1", "Character"), node("leaf2", "Character"), node("org", "Organization"), node("solo", "Character"), node("pl", "Place")],
  edges: [
    edge("m1", "hub", "org", "MemberOf"), edge("m2", "leaf1", "org", "MemberOf"), edge("m3", "leaf2", "org", "MemberOf"),
    edge("l", "hub", "pl", "LocatedIn"),
  ],
});

// R7 replaced the "principal filter + folding" suite. Those tests asserted that
// `visibleGraph` DROPPED nodes by degree and by kind — exactly the client-side filtering
// retrofit rule 6 forbids, and the reason defect D3 could not be measured from outside
// the browser. The property worth pinning is now the opposite one.
describe("no client-side filtering (retrofit rule 6)", () => {
  it("renders every node and every edge the payload contained", () => {
    const v = visibleGraph(orgWorld);
    expect(v.nodes).toHaveLength(orgWorld.nodes.length);
    expect(v.edges).toHaveLength(orgWorld.edges.length);
    expect(v.nodes.map((n) => n.id).sort()).toEqual(
      ["hub", "leaf1", "leaf2", "org", "pl", "solo"],
    );
  });

  it("keeps low-degree and unconnected nodes, which the old principal filter removed", () => {
    const ids = visibleGraph(orgWorld).nodes.map((n) => n.id);
    expect(ids).toContain("solo"); // degree 0
    expect(ids).toContain("leaf1"); // degree 1
    expect(ids).toContain("pl"); // degree 1, and not a person
  });

  it("keeps organisations and places: which TYPES are drawn is the server's decision", () => {
    const v = visibleGraph(orgWorld);
    expect(v.nodes.find((n) => n.kind === "order")).toBeDefined();
    expect(v.nodes.find((n) => n.kind === "place")).toBeDefined();
  });

  it("holds on a real fenced payload too, not just the synthetic world", () => {
    const vm = buildViewModel(g(raw3));
    const v = visibleGraph(vm);
    expect(v.nodes).toHaveLength(vm.nodes.length);
    expect(v.edges).toHaveLength(vm.edges.length);
  });

  // The honest form of "rendered count == payload count". Node counts ARE equal. Edge
  // counts are NOT, and saying so matters: §7.3 merges parallel edges into one line per
  // pair, so 18 payload edges can draw as 13 lines. That is a drawing decision, not a
  // filter -- nothing is dropped, and R7 makes the merged line name every relation it
  // absorbed (see edgeLabel). What must hold is that the drawn set is a faithful
  // re-grouping of the payload: same node ids, and every payload edge accounted for by
  // exactly one drawn line between its endpoints.
  it("draws every payload node, and accounts for every payload edge", () => {
    const payload = g(raw4);
    const vm = buildViewModel(payload);
    const v = visibleGraph(vm);

    const drawable = payload.nodes.filter((x) => kindOf(x.data.type) !== null);
    expect(v.nodes.map((n) => n.id).sort()).toEqual(drawable.map((x) => x.data.id).sort());

    const pairOf = (a: string, b: string) => (a < b ? `${a}|${b}` : `${b}|${a}`);
    const drawnPairs = new Set(v.edges.map((e) => pairOf(e.source, e.target)));
    const totalRelations = v.edges.reduce((sum, e) => sum + e.relations.length, 0);
    let accounted = 0;
    for (const { data } of payload.edges) {
      const endpointsDrawn = v.nodes.some((n) => n.id === data.source) && v.nodes.some((n) => n.id === data.target);
      if (!endpointsDrawn) continue; // the server never sent one of these endpoints
      expect(drawnPairs.has(pairOf(data.source, data.target))).toBe(true);
      accounted += 1;
    }
    // Every payload edge with drawn endpoints is inside exactly one line's relation list.
    expect(totalRelations).toBe(accounted);
    // And no line was invented: there are never MORE lines than payload edges.
    expect(v.edges.length).toBeLessThanOrEqual(payload.edges.length);
  });
});

describe("focus set (§8.3)", () => {
  const vm = buildViewModel(g(raw4));
  it("1 step = node + neighbours; 2 steps adds their neighbours", () => {
    const one = focusSet(vm.edges, "1", 1);
    expect([...one].sort()).toEqual(["1", "2", "4", "5", "7"]);
    const two = focusSet(vm.edges, "1", 2);
    expect(two.has("8")).toBe(true); // Queen Maela via Caelum
    expect(two.has("6")).toBe(true); // the Coil via Aldercross
  });
  it("neighbours are ordered by view-model order", () => {
    expect(neighboursOf(vm.edges, vm.nodes, "1")).toEqual(["2", "4", "5", "7"]);
  });
});

describe("zoom tiers (§7.5)", () => {
  it("classifies zoom", () => {
    expect(zoomTier(0.3)).toBe("far");
    expect(zoomTier(1)).toBe("default");
    expect(zoomTier(2)).toBe("close");
  });
  it("far tier keeps only the focus node and identity endpoints labelled", () => {
    expect(labelVisible("far", { isFocus: false, isIdentityEndpoint: false })).toBe(false);
    expect(labelVisible("far", { isFocus: true, isIdentityEndpoint: false })).toBe(true);
    expect(labelVisible("far", { isFocus: false, isIdentityEndpoint: true })).toBe(true);
    expect(labelVisible("default", { isFocus: false, isIdentityEndpoint: false })).toBe(true);
  });
  it("default tier hides MINOR labels on large casts; the focus set and the close tier show them", () => {
    const vm = buildViewModel(g(raw4));
    expect(minorLabelIds(vm.nodes, new Set(["1", "7"])).size).toBe(0); // 12 nodes: label all
    // a large cast: 60 fake people, identity endpoints ranked first, then degree
    const many = Array.from({ length: 60 }, (_, i) => ({ ...vm.nodes[0]!, id: `p${i}`, label: `P${i}`, degree: i % 7, first_seen_chapter: 1 }));
    const minor = minorLabelIds(many, new Set(["p3"]));
    expect(minor.size).toBe(60 - LABEL_BUDGET);
    expect(minor.has("p3")).toBe(false); // identity endpoint always labelled (degree 3)
    expect(minor.has("p6")).toBe(false); // degree 6: top rank
    expect(minor.has("p0")).toBe(true); // degree 0
    expect(labelVisible("default", { isFocus: false, isIdentityEndpoint: false, isMinor: true })).toBe(false);
    expect(labelVisible("default", { isFocus: false, isIdentityEndpoint: false, isMinor: true, inFocusSet: true })).toBe(true);
    expect(labelVisible("close", { isFocus: false, isIdentityEndpoint: false, isMinor: true })).toBe(true);
  });
});

describe("label declutter (§7.2)", () => {
  it("defers the lower-ranked of any colliding pair, keeps non-colliding labels", () => {
    const deferred = declutterLabels([
      { id: "a", box: { x1: 0, y1: 0, x2: 100, y2: 20 } },
      { id: "b", box: { x1: 50, y1: 10, x2: 150, y2: 30 } }, // overlaps a → deferred
      { id: "c", box: { x1: 200, y1: 0, x2: 300, y2: 20 } }, // clear
      { id: "d", box: { x1: 100, y1: 0, x2: 200, y2: 20 } }, // touches a and c at the edge only → kept
    ]);
    expect([...deferred]).toEqual(["b"]);
  });
});

describe("search (fenced labels only, F4)", () => {
  it("matches only names in the payload it is given", () => {
    const at3 = buildViewModel(g(raw3));
    expect(searchNames(at3, "veris").map((n) => n.label)).toEqual(["Lady Veris"]);
    const at1 = buildViewModel(g(raw1));
    expect(searchNames(at1, "veris")).toEqual([]);
    expect(searchNames(at1, "")).toEqual([]);
  });
  it("ranks prefix matches first", () => {
    const vm = buildViewModel(g(raw4));
    expect(searchNames(vm, "the")[0]?.label.toLowerCase().startsWith("the")).toBe(true);
  });
});

describe("node size (§7.1)", () => {
  it("clamps person size and fixes the others", () => {
    const vm = buildViewModel(g(raw4));
    expect(nodeSize(vm.byId.get("1")!)).toBeCloseTo(18); // degree 4 → 12 + 6
    expect(nodeSize(vm.byId.get("2")!)).toBe(16); // place
    expect(nodeSize(vm.byId.get("4")!)).toBe(20); // item
  });
});
