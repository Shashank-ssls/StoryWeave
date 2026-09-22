import { describe, expect, it } from "vitest";
import { buildViewModel } from "./viewModel";
import { chronicleRows, columnLayout, identityTimeline, stitches, SMALL_COL, LARGE_COL, LARGE_BLOCK } from "./chronicleModel";
import type { ArcModel, GraphElements } from "../types";
import raw1 from "../../tests/fixtures/hollow-crown/graph-n1.json";
import raw2 from "../../tests/fixtures/hollow-crown/graph-n2.json";
import raw3 from "../../tests/fixtures/hollow-crown/graph-n3.json";
import raw4 from "../../tests/fixtures/hollow-crown/graph-n4.json";

const g = (p: unknown): GraphElements => (p as { elements: GraphElements }).elements;
const [n1, n2, n3, n4] = [g(raw1), g(raw2), g(raw3), g(raw4)];

describe("chronicleRows", () => {
  it("orders people (principal filter) before orders before places, each degree-sorted", () => {
    const vm = buildViewModel(n4);
    const rows = chronicleRows(vm, "everyone");
    const groups = rows.map((r) => r.group);
    const firstOrder = groups.indexOf("order");
    const firstPlace = groups.indexOf("place");
    expect(groups.slice(0, firstOrder === -1 ? groups.length : firstOrder).every((g) => g === "person")).toBe(true);
    if (firstOrder !== -1 && firstPlace !== -1) expect(firstOrder).toBeLessThan(firstPlace);
  });

  it("principal cast size drops degree-1 non-identity people (same rule as the Stemma)", () => {
    const vm = buildViewModel(n1);
    const everyone = chronicleRows(vm, "everyone").map((r) => r.node.id);
    const principal = chronicleRows(vm, "principal").map((r) => r.node.id);
    expect(principal.length).toBeLessThanOrEqual(everyone.length);
  });
});

describe("columnLayout", () => {
  it("small mode: 240px columns, sealed band immediately after the bookmark, width == colWidth", () => {
    const l = columnLayout(4);
    expect(l.mode).toBe("small");
    expect(l.colWidth).toBe(SMALL_COL);
    expect(l.colX(1)).toBe(0);
    expect(l.colX(4)).toBe(3 * SMALL_COL);
    expect(l.sealedX).toBe(4 * SMALL_COL);
    expect(l.sealedWidth).toBe(SMALL_COL);
    expect(l.bands).toEqual([]);
  });

  it("F3: sealed band width is constant regardless of bookmark, within a mode", () => {
    expect(columnLayout(1).sealedWidth).toBe(columnLayout(12).sealedWidth);
    expect(columnLayout(13).sealedWidth).toBe(columnLayout(600).sealedWidth);
  });

  it("large mode (bookmark > 12): proportional narrow columns + blocks-of-50 header bands", () => {
    const l = columnLayout(120);
    expect(l.mode).toBe("large");
    expect(l.colWidth).toBe(LARGE_COL);
    expect(l.bands.length).toBe(Math.ceil(120 / LARGE_BLOCK));
    expect(l.bands[0]).toMatchObject({ label: "Chapters 1–50" });
    const last = l.bands[l.bands.length - 1]!;
    expect(last.label).toBe("Chapters 101–120");
    expect(l.sealedX).toBe(120 * LARGE_COL);
  });

  it("boundary: bookmark exactly 12 is still small mode, 13 is large", () => {
    expect(columnLayout(12).mode).toBe("small");
    expect(columnLayout(13).mode).toBe("large");
  });

  // D6/F6 (integration phase): arc-named bands replace blocks-of-50 when a work has
  // arcs configured; small mode never grows bands, arc or not.
  const ARCS: ArcModel[] = [
    { ordinal: 1, name: "The Mourning Bell", start_chapter: 1, end_chapter: 8 },
    { ordinal: 2, name: "The Salt Cipher", start_chapter: 9, end_chapter: 16 },
    { ordinal: 3, name: null, start_chapter: 17, end_chapter: 26 }, // not started yet
  ];

  it("large mode with arcs: bands use the real names instead of Chapters a-b", () => {
    const l = columnLayout(16, ARCS);
    expect(l.mode).toBe("large");
    expect(l.bands).toEqual([
      { label: "The Mourning Bell", x: 0, width: 8 * LARGE_COL },
      { label: "The Salt Cipher", x: 8 * LARGE_COL, width: 8 * LARGE_COL },
    ]);
  });

  it("F6: an arc whose name is redacted (null) still bands with the generic label", () => {
    // Bookmark 20 is inside arc 3's range (17-26), which arrives with name: null
    // (the server hasn't revealed it yet). The RANGE still bands normally — chapter
    // numbers alone aren't spoiler-bearing — just with "Arc N · chapters a-b"
    // instead of the real title.
    const l = columnLayout(20, ARCS);
    expect(l.bands.length).toBe(3);
    expect(l.bands[2]).toMatchObject({ label: "Arc 3 · chapters 17–26" });
  });

  it("F6: an arc that hasn't started at all yet contributes no band", () => {
    // bookmark 14: large mode (>12), but arc 3 (starts ch17) hasn't begun.
    const l = columnLayout(14, ARCS);
    expect(l.bands.length).toBe(2);
  });

  it("small mode ignores arcs entirely — no bands below the 12-chapter threshold", () => {
    expect(columnLayout(8, ARCS).bands).toEqual([]);
  });

  it("no arcs configured (Hollow Crown): falls back to blocks-of-50, unchanged", () => {
    const l = columnLayout(120, []);
    expect(l.bands[0]).toMatchObject({ label: "Chapters 1–50" });
  });
});

describe("stitches", () => {
  it("includes only non-identity edges between two visible rows", () => {
    const vm = buildViewModel(n3);
    const visible = new Set(vm.nodes.map((n) => n.id));
    const s = stitches(vm, visible);
    expect(s.every((x) => x.edge.kind !== "identity")).toBe(true);
    // e13 (ALIAS, identity) must never appear as a stitch
    expect(s.some((x) => x.edge.id === "e13")).toBe(false);
  });

  it("drops a stitch when either endpoint is filtered out", () => {
    const vm = buildViewModel(n3);
    const s = stitches(vm, new Set(["1"])); // only Wren visible
    expect(s).toEqual([]);
  });
});

describe("identityTimeline", () => {
  it("reconstructs the real demo's timeline: e12 normal at ch.2, e13 normal at ch.3, e14 deepen at ch.4", () => {
    const history = new Map<number, GraphElements>([[1, n1], [2, n2], [3, n3], [4, n4]]);
    const timeline = identityTimeline(history, 4);
    expect(timeline).toHaveLength(3);
    expect(timeline[0]).toMatchObject({ kind: "normal", pair: ["1", "7"] });
    expect(timeline[0]!.edge.id).toBe("e12");
    expect(timeline[1]).toMatchObject({ kind: "normal", pair: ["11", "12"] });
    expect(timeline[1]!.edge.id).toBe("e13");
    expect(timeline[2]).toMatchObject({ kind: "deepen", pair: ["1", "7"] });
    expect(timeline[2]!.edge.id).toBe("e14");
    expect(timeline[2]!.previousEdge?.id).toBe("e12");
  });

  it("stops accumulating past the given bookmark, even if more history is cached", () => {
    const history = new Map<number, GraphElements>([[1, n1], [2, n2], [3, n3], [4, n4]]);
    const timeline = identityTimeline(history, 2);
    expect(timeline).toHaveLength(1);
    expect(timeline[0]!.edge.id).toBe("e12");
  });

  it("a fully missing chain degrades to per-chapter 'normal' rather than crashing or guessing", () => {
    // Only the bookmark's own chapter is cached (1-3 were never fetched/backfilled) —
    // each payload is a full snapshot, not a delta, so a gap only loses history when NONE
    // of the earlier chapters are available at all (a partial gap is harmless: e.g. n3
    // alone already carries e12, since every payload reflects everything revealed by n).
    const history = new Map<number, GraphElements>([[4, n4]]);
    const timeline = identityTimeline(history, 4);
    // both identity edges still present at n4 surface as "normal" (nothing to deepen from)
    expect(timeline.every((r) => r.kind === "normal")).toBe(true);
    const e14 = timeline.find((r) => r.edge.id === "e14");
    expect(e14).toMatchObject({ kind: "normal", pair: ["1", "7"] }); // deepening lost — no earlier state was ever seen
  });

  it("a partial gap (one missing middle chapter) is harmless: later full-snapshot payloads already carry the earlier reveal", () => {
    const history = new Map<number, GraphElements>([[1, n1], [3, n3], [4, n4]]); // n2 missing
    const timeline = identityTimeline(history, 4);
    expect(timeline.find((r) => r.edge.id === "e14")).toMatchObject({ kind: "deepen" });
  });

  it("empty history yields an empty timeline", () => {
    expect(identityTimeline(new Map(), 4)).toEqual([]);
  });
});
