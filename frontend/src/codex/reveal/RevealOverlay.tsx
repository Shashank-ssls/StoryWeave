import { useEffect, useRef, useState } from "react";
import Button from "../../components/Button/Button";
import { ChevronLeftIcon, ChevronRightIcon, EyeIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "../chapter/roman";
import { IDENTITY_COPY } from "../../graph/viewModel";
import type { Reveal } from "../../graph/diff";
import type { LabelLookup } from "./RevealContext";
import styles from "./RevealOverlay.module.css";

// DESIGN_SPEC.md §6.5 Reveal moment + §8.2 choreography. Layout and timings below are
// deliberately verbatim from the spec table — see RevealOverlay.module.css for the actual
// animation keyframes/delays; this file is markup + interaction (focus trap, Esc,
// click-outside, pager keys, deferred focus/pointer-events until "focusable").

const FOCUS_DELAY_MS = 1250; // §8.2: buttons become focusable at t=1250
const FOCUS_DELAY_REDUCED_MS = 200; // §4.5 reduced motion: single 200ms fade

function label(byId: LabelLookup, id: string): string {
  return byId.get(id)?.label ?? "?";
}

/** `{a}`/`{b}` split for the headline — the entity names render plain, the connecting
 *  words ("is", "now lives on as", "reborn") render in --accent-hi (§6.5 item 3). */
function headlineParts(sentence: string, aLabel: string, bLabel: string): { key: number; text: string; accent: boolean }[] {
  return sentence.split(/(\{a\}|\{b\})/).map((p, i) => {
    if (p === "{a}") return { key: i, text: aLabel, accent: false };
    if (p === "{b}") return { key: i, text: bLabel, accent: false };
    return { key: i, text: p, accent: true };
  });
}

export interface RevealOverlayProps {
  reveal: Reveal;
  byId: LabelLookup;
  pageIndex: number;
  pageTotal: number;
  reducedMotion: boolean;
  onClose(): void;
  onPrev(): void;
  onNext(): void;
  onOpenDossier(entityId: string): void;
  onOpenStemma(entityId: string): void;
  onSetQuiet(v: boolean): void;
}

export default function RevealOverlay({
  reveal,
  byId,
  pageIndex,
  pageTotal,
  reducedMotion,
  onClose,
  onPrev,
  onNext,
  onOpenDossier,
  onOpenStemma,
  onSetQuiet,
}: RevealOverlayProps): JSX.Element {
  const { edge, previousEdge, kind } = reveal;
  const copy = IDENTITY_COPY[edge.relation] ?? IDENTITY_COPY.ALIAS!;
  const aLabel = label(byId, edge.source);
  const bLabel = label(byId, edge.target);
  const parts = headlineParts(copy.sentence, aLabel, bLabel);
  const announcement = fillTemplate(copy.sentence, { a: aLabel, b: bLabel });

  const beforeLine =
    kind === "deepen" && previousEdge
      ? fillTemplate(codexTheme.revealBefore, {
          sentence: fillTemplate(
            (IDENTITY_COPY[previousEdge.relation] ?? IDENTITY_COPY.ALIAS!).sentence,
            { a: label(byId, previousEdge.source), b: label(byId, previousEdge.target) },
          ),
          n: roman(previousEdge.revealed_chapter),
        })
      : null;

  const rootRef = useRef<HTMLDivElement>(null);
  const primaryRef = useRef<HTMLButtonElement>(null);
  const [ready, setReady] = useState(false);

  // Choreography's own timer: buttons become focusable (and receive focus) once the
  // actions row has faded in (§8.2 t=1250; reduced motion: 200ms, matching the collapsed
  // single fade). Re-runs on every mount, i.e. every pager page (§6.5: "each page replays
  // its choreography").
  useEffect(() => {
    const t = window.setTimeout(() => {
      setReady(true);
      primaryRef.current?.focus();
    }, reducedMotion ? FOCUS_DELAY_REDUCED_MS : FOCUS_DELAY_MS);
    return () => window.clearTimeout(t);
  }, [reducedMotion]);

  // §4.6 rule 5: the mural may brighten <=10% for the duration of the reveal only, and
  // never under reduced motion (§4.5, §8.2 item 9).
  useEffect(() => {
    if (reducedMotion) return;
    document.documentElement.setAttribute("data-reveal-active", "");
    return () => document.documentElement.removeAttribute("data-reveal-active");
  }, [reducedMotion]);

  // Window-level (not the content div's onKeyDown): focus doesn't land inside the overlay
  // until the choreography's own delay (up to 1250ms — see the effect above), and a keydown
  // handler on a div only ever sees events that bubble from a focused DESCENDANT of it. Esc/
  // click-outside must close the overlay immediately regardless of focus (§6.5 item "Esc or
  // clicking outside closes"), so this is scoped to the window like ChapterChrome's `[`/`]`.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (pageTotal > 1) {
        if (e.key === "ArrowLeft" && pageIndex > 0) { e.preventDefault(); onPrev(); return; }
        if (e.key === "ArrowRight" && pageIndex < pageTotal - 1) { e.preventDefault(); onNext(); return; }
      }
      if (e.key !== "Tab" || !rootRef.current) return;
      const focusable = Array.from(
        rootRef.current.querySelectorAll<HTMLElement>('button:not([disabled]):not([tabindex="-1"])'),
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      const inside = rootRef.current.contains(document.activeElement);
      if (e.shiftKey && (!inside || document.activeElement === first)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (!inside || document.activeElement === last)) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [pageIndex, pageTotal, onClose, onPrev, onNext]);

  return (
    <div
      className={`${styles.backdrop} ${reducedMotion ? "" : styles.brightened}`}
      data-testid="reveal-overlay"
      data-kind={kind}
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className={styles.vignette} aria-hidden="true" />
      <div className={styles.glow} aria-hidden="true" />
      <div
        ref={rootRef}
        className={`${styles.content} ${reducedMotion ? styles.reduced : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={announcement}
      >
        {pageTotal > 1 && (
          <div className={styles.pager} data-testid="reveal-pager">
            <Button
              variant="icon"
              className={styles.pagerButton}
              aria-label={codexTheme.revealPrevPage}
              disabled={pageIndex === 0}
              onClick={onPrev}
              data-testid="reveal-pager-prev"
            >
              <ChevronLeftIcon size={16} />
            </Button>
            <span data-testid="reveal-pager-label">{fillTemplate(codexTheme.revealPageOf, { i: pageIndex + 1, n: pageTotal })}</span>
            <Button
              variant="icon"
              className={styles.pagerButton}
              aria-label={codexTheme.revealNextPage}
              disabled={pageIndex === pageTotal - 1}
              onClick={onNext}
              data-testid="reveal-pager-next"
            >
              <ChevronRightIcon size={16} />
            </Button>
          </div>
        )}

        <p className={styles.kicker} data-testid="reveal-kicker">
          {fillTemplate(codexTheme.revealKickerLine, {
            n: roman(edge.revealed_chapter),
            kicker: kind === "deepen" ? codexTheme.revealKickerDeepen : codexTheme.revealKicker,
          })}
        </p>

        <div className={styles.connector} data-testid="reveal-connector">
          <div className={styles.sealCol}>
            <div className={styles.seal} />
            <div className={styles.sealName}>{aLabel}</div>
          </div>
          <div className={styles.threadWrap}>
            <div className={styles.thread} data-testid="reveal-thread" />
            <div className={styles.eyeWrap} data-testid="reveal-eye">
              <EyeIcon size={24} />
            </div>
          </div>
          <div className={styles.sealCol}>
            <div className={styles.seal} />
            <div className={styles.sealName}>{bLabel}</div>
          </div>
        </div>

        <h1 className={styles.headline} data-testid="reveal-headline">
          {parts.map((p) => (p.accent ? <span key={p.key} className={styles.link}>{p.text}</span> : <span key={p.key}>{p.text}</span>))}
        </h1>
        {/* Screen readers don't need to wait for the choreography — the full sentence is
            available as soon as it's in the DOM (§8.2: aria-live="assertive"). */}
        <div className={styles.srOnly} role="status" aria-live="assertive">{announcement}</div>

        <blockquote className={styles.quote} data-testid="reveal-quote">“{edge.evidence_span}”</blockquote>
        {beforeLine && <p className={styles.before} data-testid="reveal-before">{beforeLine}</p>}
        <p className={styles.caption}>{codexTheme.revealTrust}</p>

        <div className={`${styles.actions} ${ready ? "" : styles.notReady}`}>
          <Button
            ref={primaryRef}
            variant="primary"
            className={styles.button}
            tabIndex={ready ? 0 : -1}
            data-testid="reveal-open-dossier"
            onClick={() => onOpenDossier(edge.source)}
          >
            {codexTheme.revealOpenDossier}
          </Button>
          <Button
            variant="outline"
            className={styles.button}
            tabIndex={ready ? 0 : -1}
            data-testid="reveal-return"
            onClick={() => onOpenStemma(edge.source)}
          >
            {codexTheme.revealReturn}
          </Button>
        </div>
        <Button
          variant="quiet"
          className={styles.quietToggle}
          tabIndex={ready ? 0 : -1}
          data-testid="reveal-quiet-toggle"
          onClick={() => onSetQuiet(true)}
        >
          {codexTheme.revealQuietToggle}
        </Button>
      </div>
    </div>
  );
}
