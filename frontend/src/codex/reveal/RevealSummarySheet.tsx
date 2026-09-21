import { useRef, useState, type KeyboardEvent } from "react";
import Button from "../../components/Button/Button";
import { CloseIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "../chapter/roman";
import { IDENTITY_COPY } from "../../graph/viewModel";
import type { Reveal } from "../../graph/diff";
import type { LabelLookup } from "./RevealContext";
import styles from "./RevealSummarySheet.module.css";

// DESIGN_SPEC.md §8.1 "Jumping forward far": more than 3 reveals in one diff never play as
// sequential cinematic overlays — a single sheet lists each as a one-line sentence with its
// chapter, each expandable to the full quote (§8.4: never truncated once expanded).

function label(byId: LabelLookup, id: string): string {
  return byId.get(id)?.label ?? "?";
}

export default function RevealSummarySheet({
  reveals,
  byId,
  onClose,
}: {
  reveals: Reveal[];
  byId: LabelLookup;
  onClose(): void;
}): JSX.Element {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const rootRef = useRef<HTMLDivElement>(null);

  const toggle = (id: string): void => {
    setExpanded((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>): void => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
    }
  };

  return (
    <div
      className={styles.scrim}
      data-testid="reveal-summary-scrim"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={rootRef}
        className={styles.sheet}
        role="dialog"
        aria-modal="true"
        data-testid="reveal-summary-sheet"
        onKeyDown={onKeyDown}
      >
        <div className={styles.head}>
          <h1 className={styles.title}>{fillTemplate(codexTheme.revealSummaryTitle, { n: reveals.length })}</h1>
          <Button variant="icon" aria-label={codexTheme.close} className={styles.closeButton} onClick={onClose} autoFocus>
            <CloseIcon size={16} />
          </Button>
        </div>

        <ul className={styles.list} data-testid="reveal-summary-list">
          {reveals.map((r) => {
            const copy = IDENTITY_COPY[r.edge.relation] ?? IDENTITY_COPY.ALIAS!;
            const sentence = fillTemplate(copy.sentence, { a: label(byId, r.edge.source), b: label(byId, r.edge.target) });
            const open = expanded.has(r.edge.id);
            return (
              <li key={r.edge.id} className={styles.row} data-testid="reveal-summary-row" data-edge={r.edge.id} data-kind={r.kind}>
                <button type="button" className={styles.rowButton} onClick={() => toggle(r.edge.id)} aria-expanded={open}>
                  <div className={styles.rowLine}>
                    <span className={styles.rowKicker}>{r.kind === "deepen" ? codexTheme.revealKickerDeepen : codexTheme.revealKicker}</span>
                    <span className={styles.rowChapter}>{fillTemplate(codexTheme.chapter, { n: roman(r.edge.revealed_chapter) })}</span>
                  </div>
                  <span className={styles.rowSentence}>{sentence}</span>
                  {open && <blockquote className={styles.rowQuote}>“{r.edge.evidence_span}”</blockquote>}
                </button>
              </li>
            );
          })}
        </ul>

        <div className={styles.footer}>
          <Button variant="outline" onClick={onClose} data-testid="reveal-summary-continue">
            {codexTheme.revealSummaryClose}
          </Button>
        </div>
      </div>
    </div>
  );
}
