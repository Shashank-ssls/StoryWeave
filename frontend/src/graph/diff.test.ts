import { describe, expect, it } from "vitest";
import { diffGraphs } from "./diff";
import type { GraphElements } from "../types";
import raw1 from "../../tests/fixtures/hollow-crown/graph-n1.json";
import raw2 from "../../tests/fixtures/hollow-crown/graph-n2.json";
import raw3 from "../../tests/fixtures/hollow-crown/graph-n3.json";
import raw4 from "../../tests/fixtures/hollow-crown/graph-n4.json";

// The fixtures are REAL fenced payloads captured live at R0 (see FRONTEND_OVERHAUL §9
// Recon), so these numbers are the demo's actual reveal schedule, not made-up data.
// (Cast once: TS infers the JSON literal's `properties` too narrowly for the wire type.)
const g = (p: unknown): GraphElements => (p as { elements: GraphElements }).elements;
const [n1, n2, n3, n4] = [raw1, raw2, raw3, raw4];

describe("diffGraphs", () => {
  it("treats everything as new when there is no previous payload", () => {
    const d = diffGraphs(null, g(n1));
    expect(d.newNodes.length).toBe(g(n1).nodes.length);
    expect(d.newEdges.length).toBe(g(n1).edges.length);
  });

  it("finds the chapter-2 secret identity on the real demo data", () => {
    const d = diffGraphs(g(n1), g(n2));
    expect(d.newNodes.length).toBe(g(n2).nodes.length - g(n1).nodes.length);
    expect(d.newIdentityEdges.map((e) => e.relation)).toEqual(["SECRET_IDENTITY"]);
    // identity edges are a subset of new edges, never a separate list
    for (const e of d.newIdentityEdges) expect(d.newEdges).toContain(e);
  });

  it("finds the chapter-3 ALIAS and chapter-4 TRANSMIGRATED_INTO reveals", () => {
    expect(diffGraphs(g(n2), g(n3)).newIdentityEdges.map((e) => e.relation)).toEqual(["ALIAS"]);
    expect(diffGraphs(g(n3), g(n4)).newIdentityEdges.map((e) => e.relation)).toEqual([
      "TRANSMIGRATED_INTO",
    ]);
  });

  it("is empty when nothing changed", () => {
    const d = diffGraphs(g(n3), g(n3));
    expect(d).toEqual({ newNodes: [], newEdges: [], newIdentityEdges: [] });
  });

  it("is a pure function — inputs are not mutated", () => {
    const before = JSON.stringify(n2);
    diffGraphs(g(n1), g(n2));
    expect(JSON.stringify(n2)).toBe(before);
  });
});
