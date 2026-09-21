// The reader's bookmark, per work (DESIGN_SPEC.md §5): local state persisted in
// localStorage under `storyweave:bookmark:<slug>`, NEVER in a URL. First visit with
// nothing stored defaults to chapter 1 — the least exposure — never the last chapter.
//
// The stored value is untrusted on read: a hand-edited "999" or "abc" must never become a
// bookmark above the book's length (that would be a request above what the reader has
// confirmed, spec F1). Anything that isn't an integer in 1..chapterCount resets to 1.

export const BOOKMARK_KEY_PREFIX = "storyweave:bookmark:";

export function bookmarkKey(slug: string): string {
  return `${BOOKMARK_KEY_PREFIX}${slug}`;
}

/** Clamp-free validation: only an exact integer in 1..chapterCount is accepted. */
export function validateBookmark(raw: unknown, chapterCount: number): number {
  if (!Number.isInteger(chapterCount) || chapterCount < 1) return 1;
  const s = typeof raw === "string" ? raw.trim() : raw;
  if (typeof s !== "string" || !/^\d+$/.test(s)) return 1;
  const n = Number(s);
  if (!Number.isInteger(n) || n < 1 || n > chapterCount) return 1;
  return n;
}

export function readBookmark(slug: string, chapterCount: number): number {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(bookmarkKey(slug));
  } catch {
    /* storage unavailable (private mode, blocked) → default */
  }
  return validateBookmark(raw, chapterCount);
}

export function writeBookmark(slug: string, n: number): void {
  try {
    window.localStorage.setItem(bookmarkKey(slug), String(n));
  } catch {
    /* storage unavailable → the in-memory bookmark still works for this session */
  }
}
