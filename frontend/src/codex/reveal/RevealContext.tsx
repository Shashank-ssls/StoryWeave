import { createContext, useContext } from "react";
import type { Reveal } from "../../graph/diff";

// The UI-layer half of R6 (DESIGN_SPEC §6.5, §8.2). `ChapterProvider` (the data layer)
// only ever decides WHETHER a forward commit produced reveals (`pendingReveal`); this
// context is where "what the reveal UI is currently doing" lives — the overlay/summary
// sheet/quiet-toast state, the quiet-mode preference, the shared 3s `.just-revealed`
// highlight both the Dossier and the Stemma read, and the Dossier's "replay" entry point.
// Provided once per work by `RevealChrome`, mounted alongside `ChapterChrome` inside the
// same `ChapterProvider` in `CodexApp` — so it sits above Dossier/Stemma/Chronicle and can
// coordinate all three without any of them fetching or holding reveal state themselves.

/** Whatever a caller (Dossier's identity block, for a replay) already has in hand to
 *  resolve entity labels — a `ViewModel.byId`-shaped map is exactly this. */
export type LabelLookup = Map<string, { label: string }>;

export interface RevealContextValue {
  quiet: boolean;
  setQuiet(v: boolean): void;
  /** Opens the reveal overlay directly for one already-classified reveal — no network,
   *  no pager (a replay is always a single page). Used by the Dossier's replay button. */
  replay(reveal: Reveal, byId: LabelLookup): void;
  /** The identity edge id currently mid-glow (3s window after a reveal closes), or null.
   *  Read by EntityMain (Dossier) and StemmaCanvas to apply their own highlight. */
  justRevealedEdgeId: string | null;
}

export const RevealContext = createContext<RevealContextValue | null>(null);

export function useReveal(): RevealContextValue {
  const ctx = useContext(RevealContext);
  if (!ctx) throw new Error("useReveal must be used inside <RevealChrome>");
  return ctx;
}
