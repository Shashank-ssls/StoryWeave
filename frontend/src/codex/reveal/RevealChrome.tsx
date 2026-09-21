import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { navigate } from "../../router/useHashRoute";
import { codexTheme, fillTemplate } from "../theme";
import { useChapter } from "../chapter/ChapterProvider";
import { buildViewModel, IDENTITY_COPY } from "../../graph/viewModel";
import type { Reveal } from "../../graph/diff";
import { readRevealQuiet, writeRevealQuiet } from "./revealPrefs";
import { RevealContext, type LabelLookup, type RevealContextValue } from "./RevealContext";
import RevealOverlay from "./RevealOverlay";
import RevealSummarySheet from "./RevealSummarySheet";
import styles from "./RevealChrome.module.css";

// R6 orchestrator (DESIGN_SPEC.md §6.5, §8.2, §8.1 jump-far). Mounted once per work,
// wrapping the three tabs + ChapterChrome (CodexApp), so it sits above Dossier/Stemma/
// Chronicle and can route a forward commit's reveals to the right presentation without any
// of them fetching or holding reveal state themselves:
//   >3 reveals               -> RevealSummarySheet, regardless of quiet mode (a bare toast
//                                can't reasonably summarise a big batch; the sheet is
//                                already the non-cinematic form for that case).
//   1-3 reveals, quiet off   -> RevealOverlay with a pager.
//   1-3 reveals, quiet on    -> one toast per reveal, queued.
// A reveal NEVER fires here except via `pendingReveal`, which ChapterProvider sets ONLY
// from a forward commit's diff — never on initial load, reload, tab switch, work switch,
// backward move or a failed fetch (see ChapterProvider.requestChapter).

const QUIET_TOAST_MS = 6000;
const JUST_REVEALED_MS = 3000; // §8.2: "highlighted for 3s (glow pulse once)"

interface OverlayState {
  reveals: Reveal[];
  byId: LabelLookup;
  index: number;
}
interface QuietQueueState {
  reveals: Reveal[];
  byId: LabelLookup;
  index: number;
}

function quietSentence(r: Reveal, byId: LabelLookup): string {
  const copy = IDENTITY_COPY[r.edge.relation] ?? IDENTITY_COPY.ALIAS!;
  return fillTemplate(copy.sentence, { a: byId.get(r.edge.source)?.label ?? "?", b: byId.get(r.edge.target)?.label ?? "?" });
}

export default function RevealChrome({ children }: { children: ReactNode }): JSX.Element {
  const m = useChapter();
  const [quiet, setQuietState] = useState(() => readRevealQuiet());
  const [overlay, setOverlay] = useState<OverlayState | null>(null);
  const [summary, setSummary] = useState<{ reveals: Reveal[]; byId: LabelLookup } | null>(null);
  const [quietQueue, setQuietQueue] = useState<QuietQueueState | null>(null);
  const [justRevealedEdgeId, setJustRevealedEdgeId] = useState<string | null>(null);
  const justRevealedTimer = useRef<number | null>(null);
  const quietTimer = useRef<number | null>(null);

  const setQuiet = useCallback((v: boolean): void => {
    setQuietState(v);
    writeRevealQuiet(v);
  }, []);

  const triggerJustRevealed = useCallback((edgeId: string): void => {
    setJustRevealedEdgeId(edgeId);
    if (justRevealedTimer.current !== null) window.clearTimeout(justRevealedTimer.current);
    justRevealedTimer.current = window.setTimeout(() => setJustRevealedEdgeId(null), JUST_REVEALED_MS);
  }, []);

  // ---- forward-commit reveals arrive here, exactly once each (ChapterProvider clears
  // `pendingReveal` synchronously in the same effect that reads it). ----
  useEffect(() => {
    const pr = m.pendingReveal;
    if (!pr || !m.data) return;
    const byId: LabelLookup = buildViewModel(m.data).byId;
    if (pr.reveals.length > 3) {
      setSummary({ reveals: pr.reveals, byId });
    } else if (quiet) {
      setQuietQueue({ reveals: pr.reveals, byId, index: 0 });
    } else {
      setOverlay({ reveals: pr.reveals, byId, index: 0 });
    }
    m.dismissReveal();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m.pendingReveal]);

  // ---- quiet-mode toast queue: one at a time, auto-advances ----
  useEffect(() => {
    if (!quietQueue) return;
    if (quietTimer.current !== null) window.clearTimeout(quietTimer.current);
    quietTimer.current = window.setTimeout(() => {
      setQuietQueue((q) => (q && q.index + 1 < q.reveals.length ? { ...q, index: q.index + 1 } : null));
    }, QUIET_TOAST_MS);
    return () => {
      if (quietTimer.current !== null) window.clearTimeout(quietTimer.current);
    };
  }, [quietQueue]);

  const closeOverlay = useCallback((): void => {
    setOverlay((o) => {
      if (o) triggerJustRevealed(o.reveals[o.index]!.edge.id);
      return null;
    });
  }, [triggerJustRevealed]);

  const openFromQuiet = useCallback((): void => {
    setQuietQueue((q) => {
      if (!q) return q;
      setOverlay({ reveals: [q.reveals[q.index]!], byId: q.byId, index: 0 });
      return q.index + 1 < q.reveals.length ? { ...q, index: q.index + 1 } : null;
    });
  }, []);

  const openDossier = useCallback((entityId: string): void => {
    closeOverlay();
    navigate({ name: "work-entity", slug: m.slug, entityId });
  }, [closeOverlay, m.slug]);

  const openStemma = useCallback((entityId: string): void => {
    closeOverlay();
    navigate({ name: "work-web", slug: m.slug, focus: entityId });
  }, [closeOverlay, m.slug]);

  const replay = useCallback((reveal: Reveal, byId: LabelLookup): void => {
    setOverlay({ reveals: [reveal], byId, index: 0 });
  }, []);

  const ctx: RevealContextValue = { quiet, setQuiet, replay, justRevealedEdgeId };

  const reducedMotion = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return (
    <RevealContext.Provider value={ctx}>
      {children}

      {overlay && (
        <RevealOverlay
          key={`${overlay.reveals[overlay.index]!.edge.id}-${overlay.index}`}
          reveal={overlay.reveals[overlay.index]!}
          byId={overlay.byId}
          pageIndex={overlay.index}
          pageTotal={overlay.reveals.length}
          reducedMotion={reducedMotion}
          onClose={closeOverlay}
          onPrev={() => setOverlay((o) => (o ? { ...o, index: Math.max(0, o.index - 1) } : o))}
          onNext={() => setOverlay((o) => (o ? { ...o, index: Math.min(o.reveals.length - 1, o.index + 1) } : o))}
          onOpenDossier={openDossier}
          onOpenStemma={openStemma}
          onSetQuiet={setQuiet}
        />
      )}

      {summary && (
        <RevealSummarySheet
          reveals={summary.reveals}
          byId={summary.byId}
          onClose={() => setSummary(null)}
        />
      )}

      {quietQueue && (
        <div className={styles.toast} role="status" aria-live="polite" data-testid="reveal-quiet-toast" data-kind={quietQueue.reveals[quietQueue.index]!.kind}>
          <div className={styles.toastBody}>
            <span className={styles.toastKicker}>
              {quietQueue.reveals[quietQueue.index]!.kind === "deepen" ? codexTheme.revealKickerDeepen : codexTheme.revealKicker}
            </span>
            <span>{quietSentence(quietQueue.reveals[quietQueue.index]!, quietQueue.byId)}</span>
          </div>
          <div className={styles.toastActions}>
            <button type="button" className={styles.toastLink} onClick={openFromQuiet} data-testid="reveal-toast-evidence">
              {codexTheme.revealReadEvidence}
            </button>
            <button type="button" className={styles.toastLink} onClick={() => setQuiet(false)} data-testid="reveal-toast-show-again">
              {codexTheme.revealShowAgain}
            </button>
          </div>
        </div>
      )}
    </RevealContext.Provider>
  );
}
