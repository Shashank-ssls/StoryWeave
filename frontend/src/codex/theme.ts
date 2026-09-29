// The Codex theme's copy (DESIGN_SPEC.md §12). ALL user-facing theme copy in new
// (post-R1) components comes from here — never hardcoded inline — so a future per-work
// theme (Reliquary, Drowned, Velvet Court — see spec §4.6) can swap this whole object.
// Every key from the §12 table is present, plus the three tab labels the table doesn't
// spell out on its own (`web` already names the Stemma tab; `dossierTab`
// are this phase's own addition to complete the set).
//
// Geometry-scaffolding placeholder text in R2's screen shells ("Main content — R4") is
// NOT theme copy — it's a temporary dev marker every later phase replaces, not real
// reader-facing content, so it stays inline rather than polluting this object.

export const codexTheme = {
  web: "The Stemma",
  dossierTab: "Dossier",
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
  // D6/F6: an arc whose name hasn't been revealed yet (start_chapter > bookmark) —
  // the range alone, never the title. Literal wording per the integration brief.
  dialogArcSealed: "Arc {n} · chapters {a}–{b}",
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
  // R7: plain words, no house style. Each of these is a SERVER query parameter — the
  // client never filters a payload (retrofit rule 6) — so what the words promise and
  // what the canvas draws are the same thing by construction.
  showLabel: "Also show",
  showOrders: "Groups",
  showPlaces: "Places",
  showItems: "Items",
  showCaption: "Off by default: the graph is people unless you ask for more.",
  castSizeLabel: "Show",
  cast20: "Main cast (20)",
  cast50: "More (50)",
  castAll: "Everyone",
  castCaption: "Ranked by how much of the book so far is about them.",
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
  legendSolid: ["Solid line", "the book states it"],
  legendDashed: ["Dashed line", "implied by the surrounding text"],
  legendGlow: ["Glowing line", "a revealed identity"],
  panelHint: "Click a name to focus; click a line to read the sentence.",

  // ---- R7: the always-visible legend and the low-edge note ----
  legendTitle: "How to read this",
  legendShapes: [
    ["person", "A person"],
    ["order", "A group or house"],
    ["place", "A place"],
    ["thing", "An object"],
  ],
  legendLines: "Solid = the book states it; dashed = implied by context. Click any line to read the sentence.",
  fewEdgesLabel: "Early days",
  fewEdgesTitle: "Few stated connections yet",
  fewEdgesBody:
    "By Chapter {n} the book has named these people but not yet said much about how they " +
    "are connected. Read on, or switch to Everyone to see more of the cast.",
  // The stricter case, measured at chapter 1: the main-cast dial ranks by how much of the
  // book so far is about someone, and nobody clears that bar in the opening chapters, so
  // the default view is genuinely empty rather than merely sparse. Saying "these people"
  // when none are drawn would be a small lie on the most common first screen.
  emptyCastLabel: "Early days",
  emptyCastTitle: "No main cast yet",
  emptyCastBody:
    "By Chapter {n} nobody has appeared often enough to count as the main cast. " +
    "Choose Everyone to see whoever the book has named so far.",
  statedGroup: "The book says",
  impliedGroup: "Implied by context",
  egoEmpty: "No connections recorded for {name} by Chapter {n}.",
  egoFailed: "Could not load connections.",
  quoteFrom: "Chapter {n}",
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

  // ---- R9: responsive drawers (§11, 1024-1279 panel drawer / <1024 rail drawer) ----
  showStemmaToggle: "Show the Stemma",
  showSelectionToggle: "Show selection",
  castMenuToggle: "Cast & chapters",

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
