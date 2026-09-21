// Chapter numerals for the Codex theme (FRONTEND_OVERHAUL.md §5 Phase 3): Roman for
// n <= 39 ("Chapter IV"), Arabic above — a 400-chapter serial's "Chapter CCCXLVII" is
// unreadable, so the cut-off sits where the numeral stops being instantly legible.

const ROMAN: [number, string][] = [
  [10, "X"],
  [9, "IX"],
  [5, "V"],
  [4, "IV"],
  [1, "I"],
];

export function roman(n: number): string {
  if (!Number.isInteger(n) || n < 1) return String(n);
  if (n > 39) return String(n);
  let out = "";
  let rest = n;
  for (const [value, glyph] of ROMAN) {
    while (rest >= value) {
      out += glyph;
      rest -= value;
    }
  }
  return out;
}
