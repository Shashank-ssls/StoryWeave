import { useEffect, useId, useRef } from "react";
import Button from "../../components/Button/Button";
import { CloseIcon } from "../../icons";
import { codexTheme } from "../theme";
import styles from "./ShortcutSheet.module.css";

// DESIGN_SPEC.md §8.5 global keyboard map — the `?` shortcut sheet. Same scrim/dialog
// language as the Change-chapter dialog (§6.6): scrim, `--bg` card, real focus trap, Esc
// and click-outside close. Content is a plain list built from the theme's `shortcutRows`,
// never hardcoded here, so a future theme can relabel or reorder it.
export default function ShortcutSheet({ onClose }: { onClose(): void }): JSX.Element {
  const rootRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>): void => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
      return;
    }
    if (e.key !== "Tab" || !rootRef.current) return;
    const focusable = Array.from(
      rootRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), [tabindex]:not([tabindex="-1"])'),
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!first || !last) return;
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <div className={styles.scrim} data-testid="shortcut-scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={rootRef}
        className={styles.sheet}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="shortcut-sheet"
        onKeyDown={onKeyDown}
      >
        <div className={styles.head}>
          <h2 id={titleId} className={styles.title}>{codexTheme.shortcutsTitle}</h2>
          <Button ref={closeRef} variant="icon" aria-label={codexTheme.close} onClick={onClose}>
            <CloseIcon size={16} />
          </Button>
        </div>
        <ul className={styles.rows}>
          {codexTheme.shortcutRows.map((row) => (
            <li key={row.keys} className={styles.row}>
              <kbd className={styles.keys}>{row.keys}</kbd>
              <span className={styles.label}>{row.label}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
