import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import Button from "../../components/Button/Button";
import { CloseIcon, LockIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "./roman";
import { compactRows } from "./ChapterListCompact";
import { useChapter } from "./ChapterProvider";
import type { ArcModel } from "../../types";
import styles from "./ChapterDialog.module.css";

// Change-chapter dialog (DESIGN_SPEC §6.6). The ONLY forward path for the bookmark:
// nothing is fetched while typing — the number is pure local state until "Set bookmark"
// hands it to requestChapter, which is where §8.1 begins. A mistyped 2000 therefore can't
// flash anything on screen: it never leaves this component.

const BLOCK = 100; // D6 arc config absent (Hollow Crown, any plain ingest) → this fallback

interface DialogBlock {
  label: string;
  end: number; // the chapter the block's "Fill in Chapter N?" confirm offers
}

/** D6/F6: real arc names (already server-fenced — a not-yet-started arc's `name` is
 *  null on arrival) when the work has any configured, else the blocks-of-100
 *  fallback (spec §6.6 item 5). Each arc block confirms into its END chapter, same
 *  as a numeric block — "fill in the whole act" reads the same either way. */
function dialogBlocks(chapterCount: number, arcs: ArcModel[]): DialogBlock[] {
  if (arcs.length > 0) {
    return arcs.map((a) => ({
      label: a.name ?? fillTemplate(codexTheme.dialogArcSealed, { n: a.ordinal, a: a.start_chapter, b: a.end_chapter }),
      end: a.end_chapter,
    }));
  }
  const blocks: DialogBlock[] = [];
  for (let a = 1; a <= chapterCount; a += BLOCK) {
    const b = Math.min(a + BLOCK - 1, chapterCount);
    blocks.push({ label: fillTemplate(codexTheme.dialogBlock, { a, b }), end: b });
  }
  return blocks;
}

function parseDigits(s: string): number | null {
  return /^\d+$/.test(s) ? Number(s) : null;
}

export default function ChapterDialog(): JSX.Element | null {
  const { dialog, chapterCount, bookmark, arcs, closeDialog, requestChapter } = useChapter();
  if (!dialog.open) return null;
  return <DialogBody key={dialog.prefill} prefill={dialog.prefill} chapterCount={chapterCount}
    bookmark={bookmark} arcs={arcs} onCancel={closeDialog} onConfirm={(n) => { closeDialog(); requestChapter(n); }} />;
}

interface BodyProps {
  prefill: number;
  chapterCount: number;
  bookmark: number;
  arcs: ArcModel[];
  onCancel(): void;
  onConfirm(n: number): void;
}

function DialogBody({ prefill, chapterCount, bookmark, arcs, onCancel, onConfirm }: BodyProps): JSX.Element {
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
  const blocks = dialogBlocks(chapterCount, arcs);

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
            {blocks.map((block) => (
              <button
                key={block.end}
                type="button"
                className={styles.block}
                data-testid="dialog-block"
                onClick={() => setPendingBlock(block.end)}
                aria-pressed={pendingBlock === block.end}
              >
                {block.label}
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
