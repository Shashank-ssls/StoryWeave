/**
 * Should a keyboard shortcut stand down because the reader is typing?
 *
 * One definition, imported by all three keyboard maps (`ChapterChrome`'s `[` / `]`, the
 * Stemma's `/` + arrows + Escape, and `useGlobalShortcuts`'s `g` chord + `?`). It lived
 * as three identical private copies until R7, which is how the bug below reached all
 * three at once.
 *
 * R7: an `<input>` is only a typing target if you can actually type into it. The old
 * test was `tagName === "INPUT"`, which stood the shortcuts down whenever focus sat on a
 * CHECKBOX — and R7 put three of them (Groups / Places / Items) in the Stemma's rail, so
 * after toggling an overlay the whole keyboard went dead until the reader clicked away.
 * Found by a Playwright spec whose Escape stopped working once it ticked a checkbox.
 */
const NON_TEXT_INPUT_TYPES = new Set([
  "checkbox", "radio", "button", "submit", "reset", "range", "color", "file", "image",
]);

export function isTypingTarget(t: EventTarget | null): boolean {
  if (!(t instanceof HTMLElement)) return false;
  if (t.tagName === "TEXTAREA" || t.isContentEditable) return true;
  if (t.tagName !== "INPUT") return false;
  return !NON_TEXT_INPUT_TYPES.has((t as HTMLInputElement).type);
}
