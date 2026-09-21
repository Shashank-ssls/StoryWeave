import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import Button from "../../components/Button/Button";
import { CloseIcon, LockIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "./roman";
import { compactRows } from "./ChapterListCompact";
import { useChapter } from "./ChapterProvider";
import styles from "./ChapterDialog.module.css";

// Change-chapter dialog (DESIGN_SPEC §6.6). The ONLY forward path for the bookmark:
// nothing is fetched while typing — the number is pure local state until "Set bookmark"
// hands it to requestChapter, which is where §8.1 begins. A mistyped 2000 therefore can't
// flash anything on screen: it never leaves this component.

const BLOCK = 100; // D6 arc config is absent → blocks-of-100 fallback (spec §6.6 item 5)

function parseDigits(s: string): number | null {
  return /^\d+$/.test(s) ? Number(s) : null;
}

export default function ChapterDialog(): JSX.Element | null {
  const { dialog, chapterCount, bookmark, closeDialog, requestChapter } = useChapter();
  if (!dialog.open) return null;
  return <DialogBody key={dialog.prefill} prefill={dialog.prefill} chapterCount={chapterCount}
    bookmark={bookmark} onCancel={closeDialog} onConfirm={(n) => { closeDialog(); requestChapter(n); }} />;
}

interface BodyProps {
  prefill: number;
  chapterCount: number;
  bookmark: number;
  onCancel(): void;
  onConfirm(n: number): void;
}

function DialogBody({ prefill, chapterCount, bookmark, onCancel, onConfirm }: BodyProps): JSX.Element {
  const [value, setValue] = useState(String(prefill));
  const [pendingBlock, setPendingBlock] = useState<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const titleId = useId();
  const invalidId = useId();

  const parsed = parseDigits(value);
  const valid = parsed !== null && parsed >= 1 && parsed <= chapterCount;
  // Empty / partially typed input isn't "invalid" yet; only a number outside 1..N is.
  const showInvalid = parsed !== null && !valid;

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  // Focus trap + Esc, scoped to the dialog element itself.
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>): void => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onCancel();
      return;
    }
    if (e.key === "Enter" && e.target === inputRef.current) {
      e.preventDefault();
      if (valid && parsed !== null) onConfirm(parsed);
      return;
    }
    if (e.key !== "Tab" || !rootRef.current) return;
    const focusable = Array.from(
      rootRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
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

  const rows = compactRows(bookmark, chapterCount);
  const blocks: [number, number][] = [];
  for (let a = 1; a <= chapterCount; a += BLOCK) blocks.push([a, Math.min(a + BLOCK - 1, chapterCount)]);

  return (
    <div className={styles.scrim} data-testid="chapter-dialog-scrim" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div
        ref={rootRef}
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="chapter-dialog"
        onKeyDown={onKeyDown}
      >
        <div className={styles.head}>
          <h2 id={titleId} className={styles.title}>{codexTheme.dialogTitle}</h2>
          <Button variant="icon" aria-label={codexTheme.close} onClick={onCancel} className={styles.closeButton}>
            <CloseIcon size={16} />
          </Button>
        </div>

        <label className={styles.promptRow}>
          <span className={styles.prompt}>{codexTheme.dialogPrompt}</span>
          <input
            ref={inputRef}
            className={styles.number}
            data-testid="chapter-input"
            inputMode="numeric"
            pattern="[0-9]*"
            autoComplete="off"
            value={value}
            aria-invalid={showInvalid || undefined}
            aria-describedby={showInvalid ? invalidId : undefined}
            // Digits only: anything else is stripped before it becomes state.
            onChange={(e) => { setValue(e.target.value.replace(/\D/g, "")); setPendingBlock(null); }}
          />
          <span className={styles.prompt}>{fillTemplate(codexTheme.ofN, { n: chapterCount })}</span>
        </label>
        <p
          id={invalidId}
          className={styles.invalid}
          data-testid="chapter-invalid"
          role="status"
          aria-live="polite"
          hidden={!showInvalid}
        >
          {fillTemplate(codexTheme.dialogInvalid, { n: chapterCount })}
        </p>
        <p className={styles.helper}>{codexTheme.dialogHelper}</p>

        <ol className={styles.context} data-testid="dialog-context">
          {rows.map((row) => (
            <li key={row.n} className={`${styles.ctxRow} ${styles[row.kind]}`} data-testid={`dialog-row-${row.kind}`}>
              {row.kind === "read" ? (
                <button type="button" className={styles.ctxButton} onClick={() => { setValue(String(row.n)); setPendingBlock(null); }}>
                  <span>{fillTemplate(codexTheme.chapter, { n: roman(row.n) })}</span>
                  <span className={styles.ctxState}>{codexTheme.stateRead}</span>
                </button>
              ) : (
                <>
                  <span>{fillTemplate(codexTheme.chapter, { n: roman(row.n) })}</span>
                  <span className={row.kind === "bookmark" ? styles.ctxCurrent : styles.ctxState}>
                    {row.kind === "sealed" && <LockIcon size={16} />}
                    {row.kind === "sealed" ? codexTheme.stateSealed : codexTheme.stateCurrentBookmark}
                  </span>
                </>
              )}
            </li>
          ))}
        </ol>

        <div className={styles.serials}>
          <div className={styles.serialsLabel}>{codexTheme.dialogLongSerials}</div>
          <div className={styles.blocks}>
            {blocks.map(([a, b]) => (
              <button
                key={a}
                type="button"
                className={styles.block}
                onClick={() => setPendingBlock(b)}
                aria-pressed={pendingBlock === b}
              >
                {fillTemplate(codexTheme.dialogBlock, { a, b })}
              </button>
            ))}
          </div>
          {/* Spec §6.6 item 5: an arc/block fills the input only after the reader confirms. */}
          {pendingBlock !== null && (
            <div className={styles.blockConfirm} data-testid="block-confirm">
              <span>{fillTemplate(codexTheme.dialogBlockConfirm, { n: roman(pendingBlock) })}</span>
              <Button variant="quiet" onClick={() => { setValue(String(pendingBlock)); setPendingBlock(null); inputRef.current?.focus(); }}>
                {codexTheme.dialogYes}
              </Button>
              <Button variant="quiet" onClick={() => setPendingBlock(null)}>{codexTheme.dialogNo}</Button>
            </div>
          )}
        </div>

        <div className={styles.actions}>
          <Button
            variant="primary"
            className={styles.confirm}
            data-testid="set-bookmark"
            disabled={!valid}
            onClick={() => parsed !== null && onConfirm(parsed)}
          >
            {codexTheme.setBookmark}
          </Button>
          <Button variant="outline" className={styles.cancel} onClick={onCancel} data-testid="dialog-cancel">
            {codexTheme.cancel}
          </Button>
        </div>
        <p className={styles.footnote}>{codexTheme.dialogFootnote}</p>
      </div>
    </div>
  );
}
