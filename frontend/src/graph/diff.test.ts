import { describe, expect, it } from "vitest";
import { classifyReveal, diffGraphs } from "./diff";
import type { GraphEdgeData, GraphElements } from "../types";
import raw1 from "../../tests/fixtures/hollow-crown/graph-n1.json";
import raw2 from "../../tests/fixtures/hollow-crown/graph-n2.json";
import raw3 from "../../tests/fixtures/hollow-crown/graph-n3.json";
import raw4 from "../../tests/fixtures/hollow-crown/graph-n4.json";

// The fixtures are REAL fenced payloads captured live at R0 (see FRONTEND_OVERHAUL §9
// Recon), so these numbers are the demo's actual reveal schedule, not made-up data.
// Wren(1)/Caelum(7): SECRET_IDENTITY `e12` (revealed 2) is REPLACED at n=4 by
// TRANSMIGRATED_INTO `e14` (revealed 4) — same pair, `e12` absent from n=4. This is the
// real-world case the R6 pair-keyed diff (FRONTEND_OVERHAUL §9 "RESOLVED") exists for.
// Sparrow(11)/Veris(12): ALIAS `e13` (revealed 3), unchanged through n=4.
const g = (p: unknown): GraphElements => (p as { elements: GraphElements }).elements;
const [n1, n2, n3, n4] = [raw1, raw2, raw3, raw4];

function findEdge(payload: GraphElements, id: string): GraphEdgeData {
  const e = payload.edges.find((x) => x.data.id === id);
  if (!e) throw new Error(`fixture missing edge ${id}`);
  return e.data;
}

describe("diffGraphs", () => {
  it("treats everything as new when there is no previous payload", () => {
    const d = diffGraphs(null, g(n1));
    expect(d.newNodes.length).toBe(g(n1).nodes.length);
    expect(d.newEdges.length).toBe(g(n1).edges.length);
    expect(d.reveals).toEqual([]);
  });

  it("1->2: a NORMAL reveal for Wren/Caelum (no prior identity edge for the pair)", () => {
    const d = diffGraphs(g(n1), g(n2));
    expect(d.newNodes.length).toBe(g(n2).nodes.length - g(n1).nodes.length);
    expect(d.reveals).toHaveLength(1);
    expect(d.reveals[0]).toMatchObject({ kind: "normal", pair: ["1", "7"] });
    expect(d.reveals[0]!.edge.id).toBe("e12");
    expect(d.reveals[0]!.previousEdge).toBeUndefined();
    // every reveal's edge is also a member of newEdges — never a separate universe
    for (const r of d.reveals) expect(d.newEdges).toContain(r.edge);
  });

  it("2->3: a NORMAL reveal for Sparrow/Veris only — Wren/Caelum's e12 is unchanged (same id, same relation)", () => {
    const d = diffGraphs(g(n2), g(n3));
    expect(d.reveals).toHaveLength(1);
    expect(d.reveals[0]).toMatchObject({ kind: "normal", pair: ["11", "12"] });
    expect(d.reveals[0]!.edge.id).toBe("e13");
  });

  it("3->4: a DEEPENING reveal for Wren/Caelum (e12 SECRET_IDENTITY -> e14 TRANSMIGRATED_INTO, same pair); Sparrow/Veris's e13 is unchanged so it does not re-fire", () => {
    const d = diffGraphs(g(n3), g(n4));
    expect(d.reveals).toHaveLength(1);
    const [r] = d.reveals;
    expect(r).toMatchObject({ kind: "deepen", pair: ["1", "7"] });
    expect(r!.edge.id).toBe("e14");
    expect(r!.edge.relation).toBe("TRANSMIGRATED_INTO");
    expect(r!.previousEdge?.id).toBe("e12");
    expect(r!.previousEdge?.relation).toBe("SECRET_IDENTITY");
  });

  it("1->4 (jump-far, skips the intermediate deepening step): both pairs surface as NORMAL reveals, never deepening — there is no earlier identity edge in the OLD payload to deepen from", () => {
    const d = diffGraphs(g(n1), g(n4));
    expect(d.reveals.map((r) => r.kind)).toEqual(["normal", "normal"]);
    // ordered by revealed_chapter (Sparrow/Veris's e13 @ ch.3 before Wren/Caelum's e14 @ ch.4)
    expect(d.reveals.map((r) => r.pair)).toEqual([
      ["11", "12"],
      ["1", "7"],
    ]);
    for (const r of d.reveals) expect(r.previousEdge).toBeUndefined();
  });

  it("is empty when nothing changed", () => {
    const d = diffGraphs(g(n3), g(n3));
    expect(d).toEqual({ newNodes: [], newEdges: [], reveals: [] });
  });

  it("reveals are ordered by revealed_chapter", () => {
    // Synthetic: n1 has neither pair; n4 has both — chapter 3's pair must sort before chapter 4's.
    const d = diffGraphs(g(n1), g(n4));
    expect(d.reveals.map((r) => r.edge.revealed_chapter)).toEqual([3, 4]);
  });

  it("is a pure function — inputs are not mutated", () => {
    const before = JSON.stringify(n2);
    diffGraphs(g(n1), g(n2));
    expect(JSON.stringify(n2)).toBe(before);
  });

  it("P5/§8.4 'no quote, no edge': an identity edge with no evidence_span never produces a reveal", () => {
    const prev = g(n1);
    const withQuoteless: GraphElements = {
      nodes: g(n2).nodes,
      edges: [...g(n2).edges, { data: { ...findEdge(g(n2), "e12"), id: "e-quoteless", source: "9", target: "12", evidence_span: null } }],
    };
    const d = diffGraphs(prev, withQuoteless);
    expect(d.reveals.map((r) => r.edge.id)).toEqual(["e12"]); // the quoteless one never appears
  });

  it("P5/§8.4: a quote-less prior identity edge is treated as if it never existed, so a later quoted edge for the same pair is NORMAL, not deepening", () => {
    const base = g(n1);
    const oldQuoteless: GraphElements = {
      nodes: base.nodes,
      edges: [{ data: { ...findEdge(g(n2), "e12"), id: "e12-quoteless-draft", evidence_span: null } }],
    };
    const newQuoted = g(n2); // e12 (a different id), now with its real quote, same pair/relation
    const d = diffGraphs(oldQuoteless, newQuoted);
    expect(d.reveals).toHaveLength(1);
    expect(d.reveals[0]).toMatchObject({ kind: "normal" });
  });

  it("a same-relation edge is never a reveal even if its id changed (synthetic: an edge id bump with no relation change)", () => {
    const prev = g(n2);
    const next: GraphElements = {
      nodes: prev.nodes,
      edges: prev.edges.map((e) =>
        e.data.id === "e12" ? { data: { ...e.data, id: "e12-reissued" } } : e,
      ),
    };
    const d = diffGraphs(prev, next);
    expect(d.newEdges.map((e) => e.id)).toEqual(["e12-reissued"]); // still "new" by id...
    expect(d.reveals).toEqual([]); // ...but correctly not a reveal (same pair, same relation)
  });
});

describe("classifyReveal (Dossier replay — R6 §8.2, cache-only, no network)", () => {
  it("classifies as deepening when the earlier payload is available (exactly what a replay of Wren's ch.4 block would see)", () => {
    const e14 = findEdge(g(n4), "e14");
    const r = classifyReveal(g(n3), e14);
    expect(r).toMatchObject({ kind: "deepen", pair: ["1", "7"] });
    expect(r?.previousEdge?.id).toBe("e12");
  });

  it("falls back to normal when the earlier chapter's payload was never cached (per spec: 'otherwise as normal')", () => {
    const e14 = findEdge(g(n4), "e14");
    const r = classifyReveal(null, e14);
    expect(r).toMatchObject({ kind: "normal", pair: ["1", "7"] });
    expect(r?.previousEdge).toBeUndefined();
  });

  it("classifies as normal when the pair had no identity edge in the earlier payload (Sparrow/Veris replayed from ch.2, before their ch.3 ALIAS)", () => {
    const e13 = findEdge(g(n3), "e13");
    const r = classifyReveal(g(n2), e13);
    expect(r).toMatchObject({ kind: "normal", pair: ["11", "12"] });
  });

  it("returns null for a non-identity edge", () => {
    const social = g(n1).edges.find((e) => e.data.relation !== "SECRET_IDENTITY")!.data;
    expect(classifyReveal(g(n1), social)).toBeNull();
  });

  it("returns null (no reveal) when the pair's relation is unchanged, regardless of payload order passed to the two payloads", () => {
    const e13 = findEdge(g(n4), "e13");
    // Same fixture (n4) used as both "prev" and the edge's own home payload: the pair's
    // relation in n4 is ALIAS, matching e13's own relation -> no reveal either way.
    expect(classifyReveal(g(n4), e13)).toBeNull();
    expect(classifyReveal(g(n3), e13)).toBeNull(); // n3 already carries the same e13/ALIAS
  });
});
