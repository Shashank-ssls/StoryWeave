import { describe, expect, it } from "vitest";
import { buildViewModel } from "./viewModel";
import { edgeData } from "./stemmaModel";
import { DIRECTED_RELATIONS, R4_RELATION_LABELS, SYMMETRIC_RELATIONS } from "../ontology";
import type { GraphElements } from "../types";

// Every canvas draws its arrowheads from ONE place: `edgeData`'s `arrow` key, fed by the
// view model's `directed`, fed by `DIRECTED_RELATIONS`. This file pins that chain, because
// the bug it was written for was invisible in every other test — the Landing mini graph
// and the Dossier ego graph built edge `data` WITHOUT `arrow` at all, so the stylesheet's
// `data(arrow)` mapper had nothing to resolve and no arrowhead was ever drawn.

/** The eight directed and four symmetric halves of retrofit rule 3's closed twelve.
 *  Mirrors `SYMMETRIC_R4_RELATIONS` in `storyweave/db/models.py`, which is what the
 *  backend's own `/ego` `directed` flag is computed from. */
const R4_DIRECTED = [
  "KIN_OF", "SERVES", "MENTOR_OF", "KILLED", "MEMBER_OF", "LEADS", "OWNS", "LOCATED_IN",
] as const;
const R4_SYMMETRIC = ["ALLY_OF", "ENEMY_OF", "ROMANTIC_WITH", "SAME_AS"] as const;

function world(relation: string): GraphElements {
  return {
    nodes: [
      { data: { id: "a", label: "A", type: "Character", subtype: null, importance: 1, first_seen_chapter: 1, revealed_chapter: 1, extraction_method: "gliner", evidence_span: null, properties: {} } },
      { data: { id: "b", label: "B", type: "Character", subtype: null, importance: 1, first_seen_chapter: 1, revealed_chapter: 1, extraction_method: "gliner", evidence_span: null, properties: {} } },
    ],
    edges: [
      { data: { id: "e", source: "a", target: "b", relation, tier: 1, first_seen_chapter: 1, revealed_chapter: 1, extraction_method: "gliner", evidence_span: "A and B" } },
    ],
  } as unknown as GraphElements;
}

/** The `arrow` value the stylesheet's `target-arrow-shape: data(arrow)` will resolve. */
function arrowFor(relation: string): unknown {
  const vm = buildViewModel(world(relation), { warn: () => {} });
  expect(vm.edges, `${relation} produced no edge`).toHaveLength(1);
  return edgeData(vm.edges[0]!, "x").arrow;
}

describe("arrowheads: directed relations point at the target, symmetric ones never do", () => {
  it.each(R4_DIRECTED)("%s is drawn with an arrowhead", (relation) => {
    expect(DIRECTED_RELATIONS.has(relation)).toBe(true);
    expect(arrowFor(relation)).toBe("triangle");
  });

  it.each(R4_SYMMETRIC)("%s is drawn with NO arrowhead", (relation) => {
    expect(DIRECTED_RELATIONS.has(relation)).toBe(false);
    expect(arrowFor(relation)).toBe("none");
  });

  it("the two sets partition the closed twelve and never overlap", () => {
    const twelve = Object.keys(R4_RELATION_LABELS);
    expect(twelve).toHaveLength(12);
    for (const r of twelve) {
      expect(DIRECTED_RELATIONS.has(r) !== SYMMETRIC_RELATIONS.has(r), `${r} is in neither set or in both`).toBe(true);
    }
    for (const r of DIRECTED_RELATIONS) expect(SYMMETRIC_RELATIONS.has(r), r).toBe(false);
  });

  // The frozen Hollow Crown payload (integration rule I2) still carries v1's CamelCase
  // relation names. They were absent from `DIRECTED_RELATIONS`, so the demo — the first
  // thing a visitor sees — drew not one arrowhead.
  it.each(["LocatedIn", "MemberOf", "OwnsItem", "Serves", "Killed", "Mentor", "HasAbility", "HasTitle"])(
    "v1 relation %s is directed too, so the demo is not arrowless",
    (relation) => { expect(arrowFor(relation)).toBe("triangle"); },
  );

  it.each(["Ally", "Enemy", "Sibling", "Spouse", "Romantic"])(
    "v1 symmetric relation %s stays arrowless",
    (relation) => { expect(arrowFor(relation)).toBe("none"); },
  );

  // An arrowhead is sized as `arrow-scale` x the edge width. The old fixed 0.8 drew a
  // head smaller than the 1px line under it: in the DOM, invisible on screen.
  it("the arrowhead is never smaller than the line it sits on", () => {
    const vm = buildViewModel(world("SERVES"), { warn: () => {} });
    const d = edgeData(vm.edges[0]!, "x");
    expect(d.arrowScale as number).toBeGreaterThanOrEqual(1.3);
  });
});
