import { useEffect, useRef } from "react";
import Button from "../../components/Button/Button";
import { CloseIcon } from "../../icons";
import { codexTheme } from "../theme";
import styles from "./Landing.module.css";

// DESIGN_SPEC.md §9.2 — "How the seal works" explainer: 3 sentences + a small inline-SVG
// diagram, all copy from the theme. Same scrim/dialog language as the Change-chapter
// dialog (§6.6): 72% dimmer, Esc closes, click-outside closes.
export default function ExplainerPanel({ onClose }: { onClose(): void }): JSX.Element {
  const rootRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className={styles.explainerScrim} data-testid="explainer-scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={rootRef} className={styles.explainerPanel} role="dialog" aria-modal="true" aria-label={codexTheme.sealExplainTitle} data-testid="explainer-panel">
        <div className={styles.explainerHead}>
          <h2 className={styles.explainerTitle}>{codexTheme.sealExplainTitle}</h2>
          <Button ref={closeRef} variant="icon" aria-label={codexTheme.close} onClick={onClose}>
            <CloseIcon size={16} />
          </Button>
        </div>
        <ol className={styles.explainerSteps}>
          {codexTheme.sealExplainBody.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
        <svg className={styles.explainerDiagram} viewBox="0 0 560 60" role="img" aria-label={codexTheme.sealExplainDiagram} data-testid="explainer-diagram">
          <text x="0" y="36" className={styles.explainerDiagramText}>{codexTheme.sealExplainDiagram}</text>
        </svg>
      </div>
    </div>
  );
}
