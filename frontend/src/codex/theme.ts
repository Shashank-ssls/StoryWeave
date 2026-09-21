// The Codex theme's copy (DESIGN_SPEC.md §12). ALL user-facing theme copy in new
// (post-R1) components comes from here — never hardcoded inline — so a future per-work
// theme (Reliquary, Drowned, Velvet Court — see spec §4.6) can swap this whole object.
// Every key from the §12 table is present, plus the three tab labels the table doesn't
// spell out on its own (`web` already names the Stemma tab; `dossierTab`/`chronicleTab`
// are this phase's own addition to complete the set).
//
// Geometry-scaffolding placeholder text in R2's screen shells ("Main content — R4") is
// NOT theme copy — it's a temporary dev marker every later phase replaces, not real
// reader-facing content, so it stays inline rather than polluting this object.

export const codexTheme = {
  web: "The Stemma",
  dossierTab: "Dossier",
  chronicleTab: "Chronicle",
  personsHeading: "Of the Persons",
  fence: "The remaining leaves are sealed. Nothing past Chapter {n} was copied into this book.",
  revealKicker: "Rubric · a hidden name",
  motto: "Written in red only where the text has earned it.",
  thingsGroup: "Relics",
  loading: "Unclasping the codex…",
  lede: "first named in Chapter {c} · {k} bonds recorded",
  landingKicker: "A spoiler-sealed companion for long serials",
  landingH1: "Remember everyone. Spoil nothing.",

  // ---- R3: chapter control (DESIGN_SPEC §6.2 item 2, §6.6, §6.7, §8.1) ----
  chapter: "Chapter {n}",
  whereAreYou: "Where are you?",
  ofN: "of {n}",
  stateRead: "read",
  stateBookmark: "your bookmark",
  stateSealed: "sealed",
  stateCurrentBookmark: "current bookmark",
  changeChapter: "Change chapter",
  dialogTitle: "Where are you in the book?",
  dialogPrompt: "I have finished chapter",
  dialogHelper:
    "Type the number from your reader. Nothing is fetched until you confirm, so a mistyped 2000 can't flash anything on screen.",
  dialogInvalid: "There are only {n} chapters.",
  dialogLongSerials: "For long serials",
  dialogBlock: "Chapters {a}–{b}",
  dialogBlockConfirm: "Fill in Chapter {n}?",
  dialogYes: "Yes",
  dialogNo: "No",
  setBookmark: "Set bookmark",
  cancel: "Cancel",
  close: "Close",
  dialogFootnote: "Moving back seals what you had seen after that point, too.",
  toastForward: "Chapter {n} · {names}, {ties}",
  toastForwardIdentity: "Chapter {n} · {names}, {ties} · a name is revealed",
  toastBackward: "Bookmark moved back to Chapter {n}. Later reveals are sealed again.",
  bannerError: "Couldn't load Chapter {failed} — still showing Chapter {showing}",
  bannerErrorNothing: "Couldn't load Chapter {failed}.",
  tryAgain: "Try again",
  loadingUpTo: "Gathering everyone you've met up to Chapter {n}.",
  newNames: (k: number): string => (k === 1 ? "1 new name" : `${k} new names`),
  newTies: (k: number): string => (k === 1 ? "1 new tie" : `${k} new ties`),
} as const;

/** Fills `{token}` placeholders in a theme string, e.g. fence copy's `{n}`. */
export function fillTemplate(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = vars[key];
    return v === undefined ? `{${key}}` : String(v);
  });
}
