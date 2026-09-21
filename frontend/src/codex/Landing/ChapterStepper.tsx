import { ChevronLeftIcon, ChevronRightIcon } from "../../icons";
import { LockIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "../chapter/roman";
import styles from "./Landing.module.css";

// DESIGN_SPEC.md §6.1 — the landing try-it panel's chapter stepper. One button per
// chapter for a small book (states: read / current / next-dashed-accent / sealed);
// collapses to "‹ prev · current · next →" once the book has more than 8 chapters, per
// the spec's explicit >8 variant. The bookmark itself lives in the R3 chapter model
// (passed in), never local state here — this is a view over the SAME per-work bookmark
// the rest of the app reads and writes.
const COMPACT_ABOVE = 8;

export default function ChapterStepper({
  bookmark,
  chapterCount,
  onStep,
}: {
  bookmark: number;
  chapterCount: number;
  onStep(n: number): void;
}): JSX.Element {
  if (chapterCount > COMPACT_ABOVE) {
    const hasPrev = bookmark > 1;
    const hasNext = bookmark < chapterCount;
    return (
      <div className={styles.stepperCompact} data-testid="chapter-stepper-compact">
        <button type="button" className={styles.stepChevron} disabled={!hasPrev} aria-label="Previous chapter" onClick={() => onStep(bookmark - 1)}>
          <ChevronLeftIcon size={16} />
        </button>
        <span className={styles.stepCurrentCompact} data-testid="stepper-current">{fillTemplate(codexTheme.chapter, { n: roman(bookmark) })}</span>
        <button
          type="button"
          className={styles.stepNextCompact}
          disabled={!hasNext}
          data-testid="stepper-next"
          onClick={() => onStep(bookmark + 1)}
        >
          {fillTemplate(codexTheme.chapter, { n: roman(bookmark + 1) })} <ChevronRightIcon size={16} />
        </button>
      </div>
    );
  }

  return (
    <div className={styles.stepper} data-testid="chapter-stepper">
      {Array.from({ length: chapterCount }, (_, i) => i + 1).map((n) => {
        const kind = n < bookmark ? "read" : n === bookmark ? "current" : n === bookmark + 1 ? "next" : "sealed";
        return (
          <button
            key={n}
            type="button"
            className={`${styles.step} ${styles[`step_${kind}`]}`}
            disabled={kind === "sealed"}
            data-testid={`stepper-${kind}`}
            data-chapter={n}
            onClick={() => (kind === "read" || kind === "next") && onStep(n)}
          >
            {kind === "sealed" && <LockIcon size={16} className={styles.stepLock} />}
            {kind === "next" ? `${fillTemplate(codexTheme.chapter, { n: roman(n) })} →` : fillTemplate(codexTheme.chapter, { n: roman(n) })}
          </button>
        );
      })}
    </div>
  );
}
