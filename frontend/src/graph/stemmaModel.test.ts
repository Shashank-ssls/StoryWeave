import { describe, expect, it } from "vitest";
import { buildViewModel } from "./viewModel";
import { declutterLabels, focusSet, LABEL_BUDGET, labelVisible, minorLabelIds, neighboursOf, nodeSize, searchNames, SHOW_ALL, visibleGraph, zoomTier } from "./stemmaModel";
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

describe("principal filter + folding (§6.3 item 4)", () => {
  it("keeps degree ≥ 2, identity endpoints and the focus; folds hidden members into their org with a count", () => {
    const v = visibleGraph(orgWorld, { show: SHOW_ALL, cast: "principal", focusId: null });
    expect(v.nodes.map((n) => n.id).sort()).toEqual(["hub", "org"]); // pl has degree 1, solo 0
    expect(v.folded.get("org")).toBe(2);
    expect(v.edges.map((e) => e.id)).toEqual(["m1"]);
  });
  it("the focus is always visible, even at degree 1", () => {
    const v = visibleGraph(orgWorld, { show: SHOW_ALL, cast: "principal", focusId: "leaf1" });
    expect(v.nodes.map((n) => n.id)).toContain("leaf1");
    expect(v.folded.get("org")).toBe(1); // only leaf2 still folded
  });
  it("identity endpoints are principal regardless of degree (real n=3: Veris/Sparrow)", () => {
    const vm = buildViewModel(g(raw3));
    const v = visibleGraph(vm, { show: SHOW_ALL, cast: "principal", focusId: null });
    const ids = v.nodes.map((n) => n.id);
    expect(ids).toContain("12"); // Lady Veris, degree 1 but ALIAS endpoint
    expect(ids).toContain("11");
  });
  it("Everyone shows all drawn nodes and folds nothing", () => {
    const v = visibleGraph(orgWorld, { show: SHOW_ALL, cast: "everyone", focusId: null });
    expect(v.nodes).toHaveLength(6);
    expect(v.folded.size).toBe(0);
  });
  it("Show checkboxes remove kinds and their edges; a hidden org never gets a badge", () => {
    const v = visibleGraph(orgWorld, { show: { people: true, orders: false, places: true }, cast: "everyone", focusId: null });
    expect(v.nodes.find((n) => n.kind === "order")).toBeUndefined();
    expect(v.edges.map((e) => e.id)).toEqual(["l"]);
    const p = visibleGraph(orgWorld, { show: { people: true, orders: false, places: true }, cast: "principal", focusId: null });
    expect(p.folded.size).toBe(0);
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
