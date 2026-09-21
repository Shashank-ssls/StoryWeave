// Chronicle (timeline) view logic — DESIGN_SPEC §6.4. Pure functions over the R4 view
// model and the R3 chapter cache, unit-tested in chronicleModel.test.ts. All of it is
// computed from data the reader has already been sent (fenced payloads only), so F1-F3
// hold by construction: nothing here ever asks for, or displays, a chapter above the
// bookmark, and the sealed band's size is a constant, never a function of book length.

import { diffGraphs, type Reveal } from "./diff";
import type { GraphElements } from "../types";
import type { NodeKind, ViewModel, VmEdge, VmNode } from "./viewModel";
import { sortCast } from "./viewModel";
import { type CastSize, type ShowFilter, SHOW_ALL, visibleGraph } from "./stemmaModel";

export interface ChronicleRow {
  node: VmNode;
  group: NodeKind;
}

/** §6.4 row order: principal people first, then orders, then places/things — the same
 *  "Cast size" filter as the Stemma (§6.3 item 4), reused rather than reinvented. */
export function chronicleRows(vm: ViewModel, cast: CastSize, show: ShowFilter = SHOW_ALL): ChronicleRow[] {
  const { nodes } = visibleGraph(vm, { show, cast, focusId: null });
  const byGroup = (k: NodeKind): VmNode[] => sortCast(nodes.filter((n) => n.kind === k));
  return [
    ...byGroup("person").map((node) => ({ node, group: "person" as const })),
    ...byGroup("order").map((node) => ({ node, group: "order" as const })),
    ...byGroup("place").map((node) => ({ node, group: "place" as const })),
    ...byGroup("thing").map((node) => ({ node, group: "thing" as const })),
  ];
}

// §6.4: "240px each at small chapter counts" / "if chapters-to-bookmark > 12, columns
// become proportional ... falling back to blocks of 50". Both constants are this build's
// own pragmatic choice (the spec gives the 240px/12 figures but not a proportional-mode
// pixel width or block size) — documented in the R7 phase report, not spec-derived.
export const SMALL_COL = 240;
export const LARGE_COL = 28;
export const LARGE_BLOCK = 50;
export const SMALL_N_MAX = 12;

export interface ChronicleBand {
  label: string;
  x: number;
  width: number;
}

export interface ColumnLayout {
  mode: "small" | "large";
  colWidth: number;
  bookmark: number;
  /** Left edge of chapter n's column. */
  colX(n: number): number;
  bands: ChronicleBand[];
  sealedX: number;
  /** Always equal to `colWidth` — F3: the sealed band's size never depends on how many
   *  chapters remain, only on which layout mode is active. */
  sealedWidth: number;
  totalWidth: number;
}

export function columnLayout(bookmark: number): ColumnLayout {
  const mode: "small" | "large" = bookmark <= SMALL_N_MAX ? "small" : "large";
  const colWidth = mode === "small" ? SMALL_COL : LARGE_COL;
  const colX = (n: number): number => (n - 1) * colWidth;
  const sealedX = colX(bookmark + 1);
  const bands: ChronicleBand[] = [];
  if (mode === "large") {
    for (let start = 1; start <= bookmark; start += LARGE_BLOCK) {
      const end = Math.min(start + LARGE_BLOCK - 1, bookmark);
      bands.push({ label: `Chapters ${start}–${end}`, x: colX(start), width: colX(end) - colX(start) + colWidth });
    }
  }
  return { mode, colWidth, bookmark, colX, bands, sealedX, sealedWidth: colWidth, totalWidth: sealedX + colWidth };
}

export interface Stitch {
  edge: VmEdge;
  a: string;
  b: string;
  chapter: number;
  dotted: boolean;
}

/** §6.4 "Ties = thin curved stitches between rows at the chapter they were revealed."
 *  Every non-identity edge whose both endpoints are visible rows; identity edges get their
 *  own vertical link treatment (`identityLinks`), never a stitch. */
export function stitches(vm: ViewModel, visibleIds: Set<string>): Stitch[] {
  const out: Stitch[] = [];
  for (const edge of vm.edges) {
    if (edge.kind === "identity") continue;
    if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
    out.push({ edge, a: edge.source, b: edge.target, chapter: edge.revealed_chapter, dotted: edge.kind === "structural" });
  }
  return out;
}

/** §6.4 identity links + the R6 deepening-pair rule: replays `diffGraphs` (already
 *  unit-tested for exactly this) across every consecutive pair of cached chapters up to
 *  the bookmark, so a deepening pair naturally yields BOTH its first (normal) reveal and
 *  its later (deepen) marker as two separate timeline entries — no new classification
 *  logic needed. A gap in the cache (a chapter never fetched) breaks the chain at that
 *  point rather than guessing; `ChapterProvider.ensureHistory` is what keeps the cache
 *  gap-free in practice. */
export function identityTimeline(history: Map<number, GraphElements>, bookmark: number): Reveal[] {
  const out: Reveal[] = [];
  let prev: GraphElements | null = null;
  for (let n = 1; n <= bookmark; n++) {
    const cur = history.get(n) ?? null;
    if (!cur) {
      prev = null;
      continue;
    }
    out.push(...diffGraphs(prev, cur).reveals);
    prev = cur;
  }
  return out;
}
