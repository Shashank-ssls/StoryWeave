// The "reveal quietly" preference (DESIGN_SPEC.md §8.2): a single GLOBAL reader
// preference (not per-work — a reader who's asked for quiet reveals wants it everywhere),
// persisted in localStorage under `storyweave:revealQuiet`. Read fresh on every use rather
// than cached in a ref, so the `#/_type` dev route's toggle (§8.2: "or on the #/_type dev
// route") and the toast's own "Show reveals" link both take effect immediately for
// whichever tab currently has the work open.

export const REVEAL_QUIET_KEY = "storyweave:revealQuiet";

export function readRevealQuiet(): boolean {
  try {
    return window.localStorage.getItem(REVEAL_QUIET_KEY) === "1";
  } catch {
    return false; // storage unavailable → default to the full cinematic reveal
  }
}

export function writeRevealQuiet(quiet: boolean): void {
  try {
    if (quiet) window.localStorage.setItem(REVEAL_QUIET_KEY, "1");
    else window.localStorage.removeItem(REVEAL_QUIET_KEY);
  } catch {
    /* storage unavailable → the in-memory preference still works for this session */
  }
}
