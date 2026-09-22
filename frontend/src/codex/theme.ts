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
  ledeOne: "first named in Chapter {c} · one bond recorded",
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
  toastBackward: "Bookmark moved back to Chapter {n}. Later reveals are sealed again.",
  bannerError: "Couldn't load Chapter {failed} — still showing Chapter {showing}",
  bannerErrorNothing: "Couldn't load Chapter {failed}.",
  tryAgain: "Try again",
  loadingUpTo: "Gathering everyone you've met up to Chapter {n}.",
  newNames: (k: number): string => (k === 1 ? "1 new name" : `${k} new names`),
  newTies: (k: number): string => (k === 1 ? "1 new tie" : `${k} new ties`),

  // ---- R4: Dossier (§6.2) + states (§6.7) ----
  dramatisPersonae: "Dramatis Personae",
  ordersGroup: "Orders & Houses",
  placesGroup: "Places & Relics",
  alsoMentioned: "Also mentioned",
  changed: "changed",
  allPeople: "All {n} people →",
  allTies: "All {n} ties →",
  findName: "name or alias",
  revealedIn: "{kicker} · revealed in Chapter {n}",
  tie: "{rel} · ch. {n}",
  stemmaOf: "The Stemma of {name}",
  openFull: "open full →",
  legend: "Circle a person, square a place, diamond a thing. The accent light marks only a revealed identity.",
  fenceTooltip: "StoryWeave's server only sends chapters up to your bookmark.",
  goToPrincipal: "Go to the principal character",
  // ---- R5: The Stemma (§6.3, §7.3, §8.3) ----
  findNameLabel: "Find a name",
  showLabel: "Show",
  showPeople: "People",
  showOrders: "Orders & houses",
  showPlaces: "Places & Relics",
  castSizeLabel: "Cast size",
  castPrincipal: "Principal",
  castEveryone: "Everyone",
  castCaption: "Minor figures fold into their faction until you ask for them.",
  readTo: "Read to Chapter {n} of {m}",
  changeLink: "change",
  focusedOn: "Focused on {name} · {steps}",
  stepOne: "1 step",
  stepTwo: "2 steps",
  unfocused: "The whole web, as far as you have read",
  clearFocus: "Clear focus",
  zoomIn: "Zoom in",
  zoomOut: "Zoom out",
  stepsLabel: "Steps",
  selectedLink: "Selected link · Chapter {n}",
  selectedName: "{type} · first named in Chapter {n}",
  kindPerson: "Person",
  kindOrder: "Order or house",
  kindPlace: "Place",
  kindThing: "Relic",
  socialTitle: "{a} and {b}",
  legendSolid: ["Solid line", "a tie between two"],
  legendGlow: ["Glowing line", "a revealed identity"],
  legendFaded: ["Faded", "outside your focus"],
  panelHint: "Click a name to focus; click a line to read its evidence.",
  openDossierOf: "Open {name}'s dossier",
  topTies: "Ties",
  tooltipTie: "{rel} · Chapter {n}",
  // state cards: [label, headline, body]
  stateLoading: { label: "Loading", headline: "Unclasping the codex…", body: "Gathering everyone you've met up to Chapter {n}." },
  stateError: {
    label: "Error",
    headline: "The archive didn't answer.",
    body: "StoryWeave couldn't reach its server. Nothing was shown, and nothing past your bookmark was loaded.",
  },
  stateNoMatch: {
    label: "No match",
    headline: "No one by that name, as of Chapter {n}.",
    body: "We won't say whether they ever appear. Even that would be a spoiler.",
  },

  // ---- R6: Reveal moment (§6.5, §8.2) ----
  // (`revealKicker` itself is already defined above, from R2 scaffolding.)
  // Deepening reveal — same pair, a new (different) identity relation (FRONTEND_OVERHAUL
  // §9 "RESOLVED": Wren/Caelum's SECRET_IDENTITY -> TRANSMIGRATED_INTO at ch.4 is the real
  // case this exists for).
  revealKickerDeepen: "Rubric · the truth deepens",
  revealKickerLine: "Chapter {n} · {kicker}",
  revealTrust: "The one passage this rests on. Without a quote, no two names are ever joined.",
  revealBefore: "Before: {sentence} · Chapter {n}",
  revealOpenDossier: "Open the joined dossier",
  revealReturn: "Return to The Stemma",
  revealQuietToggle: "Reveal quietly from now on",
  revealReadEvidence: "Read the evidence",
  revealShowAgain: "Show reveals",
  revealQuietSetting: "Quiet reveals",
  revealSummaryTitle: "While you were reading: {n} identities revealed",
  revealSummaryClose: "Continue reading",
  revealPageOf: "{i} of {n}",
  revealReplayLabel: "Replay this reveal",
  revealNextPage: "Next reveal",
  revealPrevPage: "Previous reveal",

  // ---- R7: Chronicle (§6.4) ----
  chronicleSubtitle: "the chronicle, as far as you have read",
  chronicleCastSizeLabel: "Cast size",
  chronicleSealed: "sealed / never sent here",
  chronicleBookmarkLabel: "Chapter {n} · bookmark",
  chronicleNoReveals: "No identities revealed yet.",
  chronicleReveal: "{kicker} · Chapter {n}",
  chronicleExplain: "Two threads you followed separately since Chapter {a} and Chapter {b} are one person.",
  chronicleExplainDeepen: "What began in Chapter {a} goes further than you knew.",
  chronicleReadOn: "Read on to Chapter {n}",
  chroniclePrevReveal: "Previous reveal",
  chronicleNextReveal: "Next reveal",
  chronicleRevealOf: "{i} of {n}",
  chronicleTieTooltip: "{rel} · Chapter {n}",
  chronicleIdentityTooltip: "{kicker} · Chapter {n}",

  // ---- R8: Landing & states (§6.1, §6.7) ----
  landingLede:
    "StoryWeave remembers every name, tie and hidden identity a reader has met so far — " +
    "and refuses to show anything past that point. Written in red only where the text has earned it.",
  landingTrust: "The seal is enforced in the database query, not the browser. Later chapters are never sent to your screen, so there is nothing to peek at.",
  howSealWorks: "How the seal works",
  sourceLink: "Source",
  sealExplainTitle: "How the seal works",
  sealExplainBody: [
    "You tell StoryWeave which chapter you've finished — nothing more.",
    "Every request the app makes carries that number, and the server's own query filters on it: WHERE revealed_chapter <= your bookmark.",
    "A row past your bookmark is never sent, so there is nothing later for the browser to accidentally show.",
  ],
  sealExplainDiagram: "Reader → bookmark N → SQL WHERE revealed_chapter ≤ N → only those rows leave the server",
  tryTheSample: "Try the sample",
  sampleMeta: "sample novel · {n} chapters",
  landingPrompt: "Step forward. Someone is not who they seem.",
  exploreFullBook: "Explore the full book →",
  yourShelf: "Your shelf:",
  addNovel: "Add a novel",
  addNovelCaption: "paste chapters, build its map",
  openSample: "Open the sample",
  stateEmptyShelf: {
    label: "Empty shelf",
    headline: "No books on the shelf yet.",
    body: "Open the sample to see how it works, or add a novel of your own.",
  },
  stateDemoMissing: {
    label: "Setup",
    headline: "The sample book is missing.",
    body: "Run `storyweave seed-demo` to restore it.",
  },

  // ---- R9: screen-reader mirror of the focused neighbourhood (§11) ----
  focusMirrorTie: "{name} ({rel}, Chapter {n})",
  focusMirrorWithTies: "{name} — ties: {ties}",
  focusMirrorNoTies: "{name} — no ties yet recorded",
  focusMirrorNone: "Nothing focused. Choose a name from the rail, or press / to search.",

  // ---- R9: global keyboard map (§8.5) ----
  shortcutsTitle: "Keys",
  shortcutRows: [
    { keys: "g d", label: "Go to Dossier" },
    { keys: "g w", label: "Go to the Stemma" },
    { keys: "g c", label: "Go to Chronicle" },
    { keys: "[ / ]", label: "Previous / next chapter" },
    { keys: "/", label: "Search" },
    { keys: "Esc", label: "Close or unfocus" },
    { keys: "?", label: "This sheet" },
  ],
} as const;

/** Fills `{token}` placeholders in a theme string, e.g. fence copy's `{n}`. */
export function fillTemplate(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = vars[key];
    return v === undefined ? `{${key}}` : String(v);
  });
}
