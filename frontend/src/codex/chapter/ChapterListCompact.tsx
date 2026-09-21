import Button from "../../components/Button/Button";
import { LockIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "./roman";
import { useChapter } from "./ChapterProvider";
import styles from "./ChapterListCompact.module.css";

// "Where are you?" block (DESIGN_SPEC §6.2 item 2), shared by the Dossier and Stemma rails.
// At most 5 rows: the 2 previous chapters, the bookmark, and EXACTLY ONE sealed row (the
// immediately next chapter). Nothing else about the future is listed — the book's length
// appears only as "of N" (F2), and the sealed row is one fixed-size row no matter how
// many chapters remain (F3).

export type CompactRow =
  | { kind: "read"; n: number }
  | { kind: "bookmark"; n: number }
  | { kind: "sealed"; n: number };

export function compactRows(bookmark: number, chapterCount: number): CompactRow[] {
  const rows: CompactRow[] = [];
  for (let n = Math.max(1, bookmark - 2); n < bookmark; n++) rows.push({ kind: "read", n });
  rows.push({ kind: "bookmark", n: bookmark });
  if (bookmark < chapterCount) rows.push({ kind: "sealed", n: bookmark + 1 });
  return rows;
}

export default function ChapterListCompact(): JSX.Element {
  const { bookmark, chapterCount, openDialog, requestChapter } = useChapter();
  const rows = chapterCount > 0 ? compactRows(bookmark, chapterCount) : [];

  return (
    <section className={styles.block} data-testid="chapter-list" aria-label={codexTheme.whereAreYou}>
      <div className={styles.label}>
        <span>{codexTheme.whereAreYou}</span>
        {chapterCount > 0 && <span>{fillTemplate(codexTheme.ofN, { n: chapterCount })}</span>}
      </div>
      <ol className={styles.rows}>
        {rows.map((row) => (
          <li
            key={row.n}
            className={`${styles.row} ${styles[row.kind]}`}
            data-testid={`chapter-row-${row.kind}`}
            data-chapter={row.n}
            aria-current={row.kind === "bookmark" ? "true" : undefined}
          >
            {row.kind === "read" ? (
              // A past chapter is a real button: clicking steps back there (backward
              // path needs no confirm — nothing can be exposed by moving back).
              <button type="button" className={styles.rowButton} onClick={() => requestChapter(row.n)}>
                <span>{fillTemplate(codexTheme.chapter, { n: roman(row.n) })}</span>
                <span className={styles.state}>{codexTheme.stateRead}</span>
              </button>
            ) : (
              <>
                <span>{fillTemplate(codexTheme.chapter, { n: roman(row.n) })}</span>
                <span className={styles.state}>
                  {row.kind === "sealed" && <LockIcon size={16} className={styles.lock} />}
                  {row.kind === "sealed" ? codexTheme.stateSealed : codexTheme.stateBookmark}
                </span>
              </>
            )}
          </li>
        ))}
      </ol>
      <Button
        variant="outline"
        className={styles.changeButton}
        onClick={() => openDialog()}
        disabled={chapterCount < 1}
        data-testid="change-chapter"
      >
        {codexTheme.changeChapter}
      </Button>
    </section>
  );
}
