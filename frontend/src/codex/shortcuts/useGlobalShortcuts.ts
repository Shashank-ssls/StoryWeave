import { useEffect, useRef, useState } from "react";
import type { CodexRoute } from "../../router/useHashRoute";
import { navigateToTab } from "../tabs";
import { isTypingTarget } from "../typingTarget";

// DESIGN_SPEC.md §8.5 global keyboard map: `g d` / `g w` (chord: `g` arms a short
// window, the next key picks the screen) and `?` (opens the shortcut sheet). Scoped to the
// app root via a window listener with the same typing-target guard every other global
// shortcut in this app uses (R3's `[`/`]`, Stemma's `/` and arrows) — never fires while the
// reader is typing, and never while any dialog/overlay already owns the keyboard (a `role=
// "dialog"` in the document — the Change-chapter dialog, the reveal overlay, this sheet
// itself — each already runs its own scoped Escape/Tab handling).
const CHORD_MS = 900;


function aDialogIsOpen(): boolean {
  return document.querySelector('[role="dialog"][aria-modal="true"]') !== null;
}

export function useGlobalShortcuts(route: CodexRoute): { sheetOpen: boolean; closeSheet(): void } {
  const [sheetOpen, setSheetOpen] = useState(false);
  const chordArmed = useRef(false);
  const chordTimer = useRef(0);
  const routeRef = useRef(route);
  routeRef.current = route;

  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.ctrlKey || e.metaKey || e.altKey || isTypingTarget(e.target)) return;
      if (aDialogIsOpen()) return;

      if (chordArmed.current) {
        chordArmed.current = false;
        window.clearTimeout(chordTimer.current);
        const r = routeRef.current;
        if (r.name !== "work-entity" && r.name !== "work-web") return;
        // `g c` went with the Chronicle in R7; an unmapped chord key is simply ignored.
        if (e.key === "d" || e.key === "w") {
          e.preventDefault();
          navigateToTab(e.key === "d" ? "entity" : "web", r);
        }
        return;
      }

      if (e.key === "g") {
        chordArmed.current = true;
        window.clearTimeout(chordTimer.current);
        chordTimer.current = window.setTimeout(() => { chordArmed.current = false; }, CHORD_MS);
        return;
      }

      if (e.key === "?") {
        e.preventDefault();
        setSheetOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); window.clearTimeout(chordTimer.current); };
  }, []);

  return { sheetOpen, closeSheet: () => setSheetOpen(false) };
}
