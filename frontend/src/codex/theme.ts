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
} as const;

/** Fills `{token}` placeholders in a theme string, e.g. fence copy's `{n}`. */
export function fillTemplate(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = vars[key];
    return v === undefined ? `{${key}}` : String(v);
  });
}
