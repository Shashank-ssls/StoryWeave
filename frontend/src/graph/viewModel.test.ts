import { describe, expect, it } from "vitest";
import {
  buildViewModel,
  countWords,
  edgeKindOf,
  IDENTITY_COPY,
  initialOf,
  kindOf,
  principalOf,
  sortCast,
  tieLabel,
  tiesOf,
} from "./viewModel";
import { IDENTITY_RELATIONS } from "../ontology";
import type { GraphElements } from "../types";
import raw4 from "../../tests/fixtures/hollow-crown/graph-n4.json";
import raw3 from "../../tests/fixtures/hollow-crown/graph-n3.json";

const g = (p: unknown): GraphElements => (p as { elements: GraphElements }).elements;
const n4 = g(raw4);
const n3 = g(raw3);

function node(id: string, type: string, label = id, first = 1) {
  return {
    data: {
      id, label, type, subtype: null, importance: 1, first_seen_chapter: first,
      revealed_chapter: first, extraction_method: "gliner", evidence_span: null, properties: {},
    },
  };
}
function edge(id: string, source: string, target: string, relation: string, quote: string | null = "q", rev = 1) {
  return {
    data: {
      id, source, target, relation, tier: IDENTITY_RELATIONS.has(relation) ? 3 : 1,
      first_seen_chapter: rev, revealed_chapter: rev, extraction_method: "llm", evidence_span: quote,
    },
  };
}

describe("kind mapping (§7.1)", () => {
  it("maps the four drawn kinds and excludes the rest", () => {
    expect(kindOf("Character")).toBe("person");
    expect(kindOf("Organization")).toBe("order");
    expect(kindOf("Place")).toBe("place");
    expect(kindOf("Item")).toBe("thing");
    expect(kindOf("Ability")).toBe("thing");
    expect(kindOf("Concept")).toBeNull();
    expect(kindOf("Event")).toBeNull();
    expect(kindOf("Title")).toBeNull();
  });

  it("never draws a Title node, and lists Concept/Event as 'also mentioned' (real n=4 data)", () => {
    const vm = buildViewModel(n4);
    expect(vm.nodes.find((n) => n.raw.type === "Title")).toBeUndefined();
    expect(vm.nodes.find((n) => n.label === "Prince")).toBeUndefined();
    expect(vm.alsoMentioned.map((n) => n.label).sort()).toEqual(["the Alliance", "the Glasswound"]);
    // an edge to a Title/Concept endpoint is not drawn either
    expect(vm.edges.find((e) => e.relations.includes("HasTitle"))).toBeUndefined();
  });
});

describe("edge merge (§7.3)", () => {
  it("identity absorbs the parallel social edge between the same pair (real n=3 data)", () => {
    const vm = buildViewModel(n3);
    const pair = vm.edges.filter((e) => new Set([e.source, e.target]).has("11") && new Set([e.source, e.target]).has("12"));
    expect(pair).toHaveLength(1);
    expect(pair[0]?.kind).toBe("identity");
    expect(pair[0]?.relation).toBe("ALIAS");
    expect(pair[0]?.relations.sort()).toEqual(["ALIAS", "RelatedTo"]);
    expect(pair[0]?.evidence_span).toBe("the Sparrow and Veris were one");
  });

  it("absorbs regardless of payload order (social first, then identity)", () => {
    const vm = buildViewModel({
      nodes: [node("a", "Character"), node("b", "Character")],
      edges: [edge("s", "a", "b", "Ally"), edge("i", "b", "a", "SECRET_IDENTITY", "quote", 2)],
    });
    expect(vm.edges).toHaveLength(1);
    expect(vm.edges[0]).toMatchObject({ id: "i", kind: "identity", source: "b", target: "a", revealed_chapter: 2 });
  });

  it("collapses other parallels to one edge with a relation list (earliest chapter kept)", () => {
    const vm = buildViewModel({
      nodes: [node("a", "Character"), node("b", "Character")],
      edges: [edge("x", "a", "b", "Ally", "q", 3), edge("y", "b", "a", "Rival", "q", 2)],
    });
    expect(vm.edges).toHaveLength(1);
    expect(vm.edges[0]?.relations).toEqual(["Ally", "Rival"]);
    expect(vm.edges[0]?.revealed_chapter).toBe(2);
  });

  it("drops an identity edge without evidence_span and warns (§8.4)", () => {
    const warnings: string[] = [];
    const vm = buildViewModel(
      {
        nodes: [node("a", "Character"), node("b", "Character")],
        edges: [edge("i", "a", "b", "ALIAS", null), edge("j", "a", "b", "SAME_AS", "   ")],
      },
      { warn: (m) => warnings.push(m) },
    );
    expect(vm.edges).toHaveLength(0);
    expect(warnings).toHaveLength(2);
    expect(warnings[0]).toContain("ALIAS");
  });

  it("classifies edge kinds", () => {
    expect(edgeKindOf("LocatedIn")).toBe("structural");
    expect(edgeKindOf("MemberOf")).toBe("structural");
    expect(edgeKindOf("Ally")).toBe("social");
    expect(edgeKindOf("RelatedTo")).toBe("social");
    expect(edgeKindOf("TRANSMIGRATED_INTO")).toBe("identity");
  });
});

describe("degree and cast sort (§6.2)", () => {
  it("computes degree from merged edges of the fenced payload only", () => {
    const vm = buildViewModel(n4);
    // Wren: Aldercross, Glass-sight, heron ring, Caelum (identity). Glasswound is a
    // Concept (not drawn) so that edge doesn't count.
    expect(vm.byId.get("1")?.degree).toBe(4);
    expect(principalOf(vm)?.label).toBe("Wren");
  });

  it("sorts by degree desc, then first appearance, then label", () => {
    const vm = buildViewModel({
      nodes: [node("z", "Character", "Zed", 1), node("b", "Character", "Bea", 2), node("a", "Character", "Al", 2), node("c", "Character", "Cy", 1)],
      edges: [edge("1", "z", "b", "Ally"), edge("2", "z", "a", "Ally")],
    });
    expect(sortCast(vm.nodes).map((n) => n.label)).toEqual(["Zed", "Al", "Bea", "Cy"]);
  });

  it("resolves ties with the other endpoint", () => {
    const vm = buildViewModel(n4);
    expect(tiesOf(vm, "1").map((t) => t.other.label).sort()).toEqual(["Aldercross", "Glass-sight", "Prince Caelum", "the heron ring"]);
  });
});

describe("copy (§7.4)", () => {
  it("has a sentence for every identity enum in ontology.ts", () => {
    for (const rel of IDENTITY_RELATIONS) expect(IDENTITY_COPY[rel]?.sentence).toBeTruthy();
  });
  it("labels ties in lowercase, unknown as 'linked'", () => {
    expect(tieLabel("Ally")).toBe("ally of");
    expect(tieLabel("LocatedIn")).toBe("in");
    expect(tieLabel("RelatedTo")).toBe("linked");
    expect(tieLabel("ALIAS")).toBe("alias");
  });
  it("count words up to twenty, digits above", () => {
    expect(countWords(0)).toBe("no");
    expect(countWords(5)).toBe("five");
    expect(countWords(20)).toBe("twenty");
    expect(countWords(21)).toBe("21");
  });
  it("initials skip a leading article", () => {
    expect(initialOf("Wren")).toBe("W");
    expect(initialOf("the Gray Sparrow")).toBe("G");
  });
});
