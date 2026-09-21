# StoryWeave — Frontend Design Spec: "The Heretic's Codex"

> **Status:** design-final, supersedes `DESIGN.md` (Phase 8 "constellation").
> **Scope:** UI, features, aesthetic, interaction, states. No backend code changes are assumed; every place the design needs something the backend may not provide is marked **[BACKEND DEP]** and collected in §13.
> **Companion files in this folder:**
> - `tokens.css` — every color, type, spacing, motion token as CSS custom properties (source of truth).
> - `cytoscape-style.js` — the graph stylesheet, derived from the tokens.
> - `mural-codex.svg` — the placeholder backdrop line-art (to be replaced by final art, see §4.6).
> - Visual reference: the design canvas "StoryWeave Redesign Directions", page **The Heretic's Codex** (7 artboards). Where this document and the canvas disagree, **this document wins**.

---

## 0. How to read this document (for the planning/build chat)

1. Everything in **MUST** / **MUST NOT** is a hard rule. Everything in *should* is a strong default that may be tuned after screenshots.
2. **Rule Zero still applies.** No UI phase is "green" until the build agent has rendered it in a browser, taken a screenshot, and compared it against the relevant section here. A compiling build is not a rendered UI.
3. Build order suggestion is in §15. Keep each phase at its own green, pushed boundary.
4. Label every verification as MEASURED / ASSERTED / BROKEN, as the project already does.

---

## 1. Design rationale (one paragraph)

StoryWeave is a reading companion, not an analytics dashboard, so the primary view is a **character dossier** that answers the reader's real question — *"wait, who is this again?"* — with the relationship graph and a chapter timeline as supporting views. The visual language is an **illuminated heretical manuscript**: oxblood-black vellum, warm bone ink, a blackletter display face used only at large sizes, and faint engraved marginalia at the edges of the screen. It is dark fantasy that still behaves like a professional app: ornament lives at the edges, working surfaces are clean. **Rubric red is semantic**: in medieval manuscripts red ink marked what mattered, and here it marks exactly one thing — a revealed identity. The spoiler fence, the project's core engineering claim (enforced in SQL, not the UI), is **drawn on screen** as sealed leaves of the book, so the reader can see and trust it.

---

## 2. Core principles (non-negotiable)

| # | Principle | What it means in practice |
|---|---|---|
| P1 | **Reader-first, not graph-first** | Default landing inside a novel is the Dossier of the most-connected character, not the full graph. |
| P2 | **Red means reveal** | `--accent` (rubric red) is used ONLY for identity edges, reveal moments, the bookmark marker, and the "changed" tag on cast entries. Never for buttons, links in general, hovers, decoration, or brand. |
| P3 | **The fence is visible** | Every screen that shows story data shows the bookmark and a sealed representation of what lies beyond it. |
| P4 | **The fence is never weakened by the UI** | The frontend MUST NOT request `n` greater than the confirmed bookmark, MUST NOT prefetch `n+1`, and MUST NOT display counts, placeholders, silhouettes or hints of future content (see §9). |
| P5 | **Evidence is one click away, always** | Every identity claim shows its quoted source clause inline. No quote, no edge (mirrors the backend citation gate). |
| P6 | **Ornament at the edges, clarity in the middle** | The mural never sits under the graph canvas or under body text at full strength. |
| P7 | **Shape says what, color says reveal** | Entity types are encoded by node shape and label style, not by an 8-hue palette. |
| P8 | **No developer controls in reader UI** | No entity/link counters, no "MIN LINKS", no debug readouts. Power features live behind clear reader language. |

---

## 3. What to keep / discard from the old `DESIGN.md`

**Keep**
- Gold→now **red** reserved exclusively for reveals (the idea was right; execution broke it).
- The "reveal as an event" concept (the old "bloom"), now upgraded to a full reveal moment (§8.2).
- Self-hosted fonts via `@fontsource` — no runtime CDN calls (the app is "fully local").
- Node label halo technique (text outline in background color) so labels read over edges.
- `cytoscape-cola` continuous physics with drag-and-resettle, and hover/click focus with neighbour highlighting.
- Reduced-motion handling (finite physics, reveal becomes a plain appear).
- The precomputed demo tier as the default first-run experience.

**Discard**
- The "constellation / night sky" metaphor and midnight-indigo palette.
- The 8-hue entity palette and the entity-type legend card.
- Spectral + IBM Plex pairing; all mono-uppercase-letterspaced micro-labels (`ENTITIES`, `READING POSITION`, etc.).
- Top-bar stats (`ch 4 · 13 entities · 13 links`), `MIN LINKS −/+`, `trace a path` as exposed controls.
- The full-bleed graph as the default screen.
- The linear chapter slider as the chapter control.
- The split-colour italic "Story*Weave*" wordmark; the dashed "Add a novel" card; the unexplained lock icon on the shelf card.
- Gold used on the slider track/thumb/wordmark.

---

## 4. Visual system

All values live in `tokens.css`. The table below is the human-readable version.

### 4.1 Color tokens (dark only — this theme has no light mode)

| Token | Hex / value | Role |
|---|---|---|
| `--bg` | `#150B0A` | App background (oxblood-black vellum) |
| `--deep` | `#0C0605` | Inputs, sealed zones, deepest wells |
| `--panel` | `rgba(21,11,10,0.90)` | Side rails and panels over the mural |
| `--raise` | `rgba(232,216,194,0.07)` | Selected list row, hover wash |
| `--line` | `#3A2420` | Hairlines, borders, dividers, far edges |
| `--ink` | `#E8D8C2` | Primary text, primary node fill, primary button fill |
| `--dim` | `#A8917D` | Secondary text, near edges |
| `--faint` | `#6B5548` | Tertiary text, faded (out-of-focus) nodes & labels, sealed text |
| `--mural` | `#3E2724` | Mural line-art stroke only |
| `--accent` | `#D9503A` | **Rubric red — reveals only** |
| `--accent-hi` | `#F4C0B0` | Emphasised word inside a reveal sentence |
| `--accent-soft` | `rgba(217,80,58,0.16)` | Glow halos, reveal backdrop tint |
| `--on-ink` | `#150B0A` | Text on `--ink` fills (buttons, selected chapter row) |

Contrast (measured targets, verify in build): `--ink` on `--bg` ≈ 13:1; `--dim` on `--bg` ≥ 6:1; `--accent` on `--bg` ≈ 4.4:1 — **use `--accent` for text only at ≥ 13px weight 500+ or ≥ 18px regular**. `--faint` (≈ 2.9:1) is only for de-emphasised graph labels and decorative "sealed" text, never for information the reader needs to act on.

### 4.2 Typography

| Role | Family | Use | Rule |
|---|---|---|---|
| Display | **Pirata One** (blackletter) | Novel title, page H1 (entity name), reveal headline, wordmark | **MUST NOT be used below 28px.** Never for body, labels, buttons, graph labels. |
| Body / literary | **EB Garamond** (400, 500, 600, italic) | Entity names in lists, ties, quotes, fence line, reveal sentences, graph labels | Quotes always italic. |
| UI | **Alegreya Sans** (400, 500, 700) | Buttons, inputs, small labels, chapter metadata, legends | Sentence case only. No uppercase + letter-spacing. |

Install: `@fontsource/pirata-one`, `@fontsource/eb-garamond`, `@fontsource/alegreya-sans`. Fallback stacks in `tokens.css`.

**Type scale (px):** 13 · 14 · 16 · 18 · 21 · 24 · 30 · 36 · 44 · 60 · 72 · 96.

| Usage | Size / line-height | Family |
|---|---|---|
| Entity H1 (dossier) | 96 / 0.95 | Display |
| Landing H1 | 92 / 0.95 | Display |
| Reveal headline | 70 / 1.02 | Display |
| Dialog title | 42 / 1.1 | Display |
| Panel title (selected link) | 36–38 / 1.05 | Display |
| Novel title in rail | 32 / 1.05 | Display |
| Identity sentence | 34 / 1.15 | Body |
| Quote (dossier) | 21 / 1.5 italic | Body |
| Lede under H1 | 22 italic | Body |
| List items (cast, ties) | 19–21 | Body |
| Graph node label | 17 (focus node 24 display) | Body |
| UI labels, buttons | 14–15 | UI |
| Meta / captions | 13 | UI |

Numbers: chapter numbers are shown as **Roman numerals in prose/labels** ("Chapter III") and as **Arabic digits in inputs** ("I have finished chapter [3] of 4"). Above chapter 39, switch labels to Arabic ("Chapter 412") — Roman numerals stop being readable. [Rule: `roman(n)` if n ≤ 39 else `n`.]

### 4.3 Spacing, radii, borders

- Base unit **4px**. Scale: 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80.
- Rails: left 290px, right 330–400px (see screens). Page padding: 36–56px.
- **Radii: 0.** Everything is square-cornered like a printed page. (Only exception: circular nodes and round icon glyphs.)
- Borders: 1px `--line`. Emphasised border (dialogs, primary outline buttons): 1px `--ink` or `--faint`.
- Shadows: none, except the reveal card/dialog backdrop dimmer. Depth comes from `--panel` over mural, not drop shadows.

### 4.4 Ornament

- **Section ornament rule:** a thin line with a small centred lozenge (see dossier). Used once per page under the H1. Never stacked.
- **Icons:** inline stroke SVG, 1.3–1.6px stroke, square caps, `currentColor`. No emoji, no filled icon packs. Required glyphs: chevron left/right, close (×), lock (sealed), arch-door (fence marker), eye (reveal marker), plus/minus (zoom), search.
- **The eye glyph** is the reveal marker (dossier identity block, landing try-it prompt, reveal card connector). Stroke `--accent`.

### 4.5 Motion principles

| Token | Value | Use |
|---|---|---|
| `--dur-fast` | 120ms | hover, focus ring, button press |
| `--dur-base` | 220ms | panel content swap, list highlight, tab change |
| `--dur-slow` | 420ms | dim/undim of graph focus, dialog open |
| `--dur-reveal` | 1400ms total | reveal choreography (§8.2) |
| `--ease-out` | `cubic-bezier(0.2, 0.8, 0.2, 1)` | default |
| `--ease-ink` | `cubic-bezier(0.65, 0, 0.35, 1)` | line drawing (red thread) |

Rules: nothing bounces, nothing spins, no parallax. Motion is ink settling on paper. Graph physics is the one continuous motion and it must settle within ~1.5s after any change. `prefers-reduced-motion: reduce` → physics runs a fixed number of iterations then stops; reveal becomes an instant appear with a 200ms fade; no line drawing.

### 4.6 The mural (background art)

- Engraved, monochrome line-art in `--mural` stroke on `--bg`. Subjects for this theme: double-ruled manuscript border, vine marginalia along the left/right margins, a great wheel/rota at centre, two haloed standing figures, serpentine flourishes at the lower corners.
- `mural-codex.svg` in this folder is a **placeholder sketch**. Final art should be a single SVG (preferred) or a 2x PNG/WebP, commissioned or adapted from public-domain engravings, exported already tinted to `--mural` so no runtime filtering is needed.
- **Placement rules (MUST):**
  1. Mural is a fixed, non-interactive layer (`position: fixed; z-index: 0; pointer-events: none`).
  2. A vignette layer sits above it: radial gradient, darker at edges and centre-light, so ornament shows at the margins.
  3. On the **Web** view, the graph canvas area gets a solid `--bg` centre (radial `--bg` 0–55% → transparent), so no mural line can be mistaken for an edge.
  4. Side rails use `--panel` (90% opaque) — the mural is barely visible through them.
  5. The mural MUST NOT animate, except on the Reveal screen (§8.2), where it may brighten by ≤ 10% for the duration of the reveal.
- **Per-work theme hook:** the mural and theme name are chosen per novel via config (`theme = "codex"` in `storyweave.toml`). This spec defines only the Codex theme; other themes (Reliquary, Drowned, Velvet Court) exist on the canvas as future options. **[CONFIG DEP — see §13]**

---

## 5. Information architecture

```
Landing  ──►  Novel (inside a work)
                ├── Dossier   (default tab)   /work/:slug/entity/:id
                ├── Stemma    (graph)         /work/:slug/web?focus=:id
                └── Chronicle (timeline)      /work/:slug/chronicle
              overlays:  Change chapter (dialog) · Reveal (full-screen moment)
              states:    Loading · Empty shelf · Error · Search no-match
```

- The three tabs are named **Dossier · The Stemma · Chronicle**. ("Stemma" is the manuscript-scholarship word for a family-tree diagram of texts; it is the Codex theme's name for the graph. Tab label copy is theme-provided.)
- The bookmark (current chapter) is **global per work** and persists across tabs.
- URLs should be shareable, but MUST NOT include the chapter bookmark (a shared link must not set someone else's reading position). The bookmark is local state per work, persisted in `localStorage` (`storyweave:bookmark:<slug>`).
- Current codebase has no router. Adding a lightweight router is a frontend-only decision for the build chat; hash routing is acceptable.

---

## 6. Screen-by-screen specification

Canvas artboards are 1440×900. Minimum supported viewport: **1280×720** (laptop). Below 1280 wide, see §11.

### 6.1 Landing (`Codex — 1. Landing`)

**Purpose:** show the magic in the first 10 seconds without reading.

Layout: page padding 34px 80px. Header row (wordmark left in Display 26px; right links "How the seal works" · "Source" in UI 14px `--dim`). Main row: left column 580px, 64px gap, right "try it" panel flexes. Footer row: "Your shelf:" + work titles + "Add a novel".

Left column, top to bottom:
1. Kicker — "A spoiler-sealed companion for long serials", Body/UI 18px, `--accent`. *(Allowed use of red: it names the reveal-product. If this feels like red leakage in review, switch to `--dim`.)*
2. H1 — "Remember everyone. / Spoil nothing." Display 92px, two lines.
3. Lede — Body 24px `--dim`: what it does, ending with the theme motto "Written in red only where the text has earned it."
4. Trust line — UI 15px `--dim`, max 480px: "The seal is enforced in the database query, not the browser. Later chapters are never sent to your screen, so there is nothing to peek at."

Right panel ("Try the sample"): `--panel` bg, 1px `--line`, padding 30/34.
- Title row: sample novel name (Display 30px) + "sample novel · N chapters" (UI 13px `--dim`).
- **Chapter stepper**: one button per chapter for the demo (4 for Hollow Crown). States: read (outline `--line`, text `--dim`), current (fill `--ink`, text `--on-ink`, 700), **next** (1px dashed `--accent`, text `--accent`, label "Ch. III →"), sealed (fill `--deep`, text `--faint`). For demos longer than 8 chapters show: `‹ prev` · current · `next →` only.
- Mini graph (≈560×230) rendered with the real Cytoscape style at the current demo chapter, non-interactive except hover.
- Prompt row: eye glyph + italic Body 20px "Step to Chapter III. Someone is not who they seem."
- Clicking the dashed "next" button advances the demo chapter **and plays the full Reveal moment (§8.2)** if that step crosses a reveal, then offers "Explore the full book" → enters the Dossier.

Demo requirement: first-run with no works → Landing uses the precomputed demo (no GPU/LLM). **The landing mini-graph MUST obey the fence** (only data at the demo's current chapter; no ghost of the upcoming edge).

States: fonts loading → system serif fallback, no layout shift beyond 2%; demo DB missing → hide the try-it panel, show Empty shelf (§6.7) on the right.

### 6.2 Dossier (`Codex — 2. Dossier`) — the primary screen

Three columns: **Left rail 290px** · **Main (flex)** · **Right panel 400px**.

**Left rail** (`--panel`, right border 1px `--line`, padding 30/26, gap 24):
1. Wordmark link "StoryWeave" (Body 16 `--dim`) → Landing. Novel title (Display 32).
2. **"Where are you?"** block (UI 14 `--dim` label) — the compact chapter list:
   - Shows at most 5 rows: the 2 previous chapters, the bookmark row, 1 sealed row, collapsed context. Row = "Chapter III" left, state right (italic "read" / "your bookmark" / lock glyph + "sealed").
   - Bookmark row: fill `--ink`, text `--on-ink`, 600.
   - Sealed row: fill `--deep`, text `--faint`, lock glyph. Only the **immediately next** chapter is shown as sealed; never list further future chapters by number beyond "of N".
   - Button "Change chapter" (full width, 44px, 1px `--ink` outline) → opens Change-chapter dialog (§6.6). Keyboard: `[` and `]` step back/forward one chapter (forward goes through the confirm path, §8.1).
3. **Dramatis Personae** (Body 17 `--dim` header with hairline): people list, Body 19px, 5px/10px row padding.
   - Sorted by degree (ties at bookmark) descending, then first appearance.
   - Selected row: `--raise` bg + 2px left rule `--ink` + 600 weight.
   - Entities changed at the current chapter (new entity, or gained an identity edge at exactly the bookmark chapter) get an italic `--accent` tag "changed" (13–14px). Computed client-side by diffing graph(n) vs graph(n−1). **[see §9 — both payloads are fenced; safe]**
   - Then sub-groups: "Orders & Houses" (organizations), "Places & Relics" (places, items). Sub-group items are listed inline comma/·-separated, Body 18 `--dim`, clickable.
   - Scrolls independently when long. With 100+ entities: show top 12 people, then "All 87 people →" link opening a filterable full list in the rail (search field at top).

**Main** (padding 40/56/0):
1. Row: section label "Of the Persons" (Body 16 `--dim`; theme copy) left; tabs right (UI 14; active = `--ink` + 1px underline, inactive `--dim`).
2. **H1 entity name** Display 96px/0.95.
3. **Lede** italic Body 22 `--dim`: "first named in Chapter I · five bonds recorded" (template: `first named in Chapter {first_chapter} · {degree_words} bonds recorded`).
4. Ornament rule (480px) — once.
5. **Identity block(s)** — one per identity edge touching this entity, newest reveal first. Layout: eye glyph (44px, `--accent`) + column:
   - Kicker: "Secret identity · revealed in Chapter II" (UI 14 `--accent`). Relation label mapping in §7.4.
   - Sentence: "Wren is *Prince Caelum*." Body 34px; the other entity's name in italic `--accent-hi` and is a link to that dossier.
   - Quote: italic Body 21 `--dim`, max 540px, with curly quotes. Source is the citation-gate clause. **[BACKEND DEP: quote text in payload]**
   - Link "Show it in the chapter →" (UI 14 `--accent`). **[BACKEND DEP: optional; if chapter text/offset isn't available, render "Chapter II" as plain text instead of a link]**
   - If an entity has no identity edges, this block is omitted (no empty placeholder).
6. **Ties grid** — 2 columns, 40px column gap. Each row: other entity (Body 21, link) left; relation + chapter (UI 13 `--dim`, "carries · ch. I") right; bottom hairline. Sorted by first-revealed chapter, then name. >12 ties → show 12 + "All 23 ties →".
7. Flexible spacer.
8. **Fence line** (see §9.2) pinned at the bottom of Main.

**Right panel** "The Stemma of Wren" (`--panel`, left border, padding 30/24):
- Header: title (Body 16 `--dim`) + "open full →" link to the Stemma tab focused on this entity.
- Ego graph (≈352×430): selected entity centred (large node with initial), 1-hop neighbours on a ring, 2-hop shown faint. Uses the same Cytoscape style (§7) with a `concentric` layout (not cola) for stability. Clicking a node navigates to its dossier.
- Legend line (UI 13 `--dim`): "Circle a person, square a place, diamond a thing. The accent light marks only a revealed identity."

**States:** loading (skeleton: H1 bar, 3 list bars; no spinner); entity not present at this chapter (reader moved the bookmark back past its first appearance) → the neutral "No one by that name, as of Chapter II." card (§6.7) + "Go to the principal character" link; never show the old data.

### 6.3 The Stemma — graph, focus mode (`Codex — 3. Web, focus mode`)

Three columns: **Left filter rail 290px** · **Canvas (flex)** · **Right selection panel 350px**.

**Left rail:**
1. Wordmark + novel title (as Dossier).
2. "Find a name" search input (44px, `--deep` bg). Searches name **and aliases present in the fenced payload only**. Enter/select → focus that node. No match → §6.7 no-match state inline under the field.
3. "Show" — three checkboxes (checked by default, accent-colored): People · Orders & houses · Places & Relics.
4. "Cast size" — segmented control: **Principal** (default) | **Everyone**. Caption: "Minor figures fold into their faction until you ask for them." Principal = nodes with degree ≥ 2 OR any identity edge OR is the focus; others are hidden (organization-member leaves fold into their organization node, shown as a small count badge "+4" on the org node). This replaces "MIN LINKS".
5. Spacer, then footer: "Read to Chapter III of 4 · change".

**Canvas:**
- Top bar inside canvas: left "Focused on Wren · 1 step" (Body 16 `--dim`), right the tabs.
- Graph rendering: §7. Default on open: focus on the entity passed in the URL, else the highest-degree person. Focus = the entity + 1-hop full strength, everything else `--faint` at 0.35–0.45 opacity.
- Controls bottom-left: "Clear focus" (nowrap), zoom + and − (44×44). Zoom also by wheel/pinch. Double-click empty canvas = fit.
- Background: solid `--bg` centre per mural rule 3.

**Right panel (selection):**
- If an **edge** is selected: kicker "Selected link · Chapter II" (UI 13 `--accent` if identity, else `--dim`), title "Wren is Prince Caelum" (Display 38), quote (identity only), hairline, legend rows (Solid line — a tie between two / Glowing line — a revealed identity / Faded — outside your focus), primary outline button "Open Wren's dossier".
- If a **node** is selected: name (Display 38), type + first chapter, top 5 ties, identity sentence if any, "Open dossier".
- Nothing selected: the legend and "Click a name to focus; click a line to read its evidence."

### 6.4 Chronicle — timeline (`Codex — 4. Chronicle`)

Header bar 76px (`--panel`): novel title (Display 26) + italic subtitle "the chronicle, as far as you have read" + tabs.

Body: chart (flex) + right panel 330px.

**Chart:**
- Rows = entities (principal people first, then orders, then places; same "Cast size" logic as Stemma, toggle in a small control above the chart). Row height 64px; name column 200px (Body 18; principal bold; orgs/places italic `--dim`).
- Columns = chapters, 240px each at small chapter counts. **Scaling rule:** if chapters-to-bookmark > 12, columns become proportional and the header shows arc/volume bands **[CONFIG DEP: arc names]**, falling back to blocks of 50/100 chapters. Horizontal scroll with the bookmark kept in view; opens scrolled to the bookmark.
- Per row a **presence thread**: 3px line from first appearance to the bookmark; start dot 5px. Principal = `--ink`, others `--dim`, places/orgs dotted `--faint`.
- **Ties** = thin curved stitches `--faint` between rows at the chapter they were revealed.
- **Identity reveals** = vertical 3px `--accent` link between the two rows at the reveal chapter, ringed dots at both ends, small UI 13 `--accent` label ("secret identity", "alias"). The currently selected one gets a soft `--accent-soft` capsule behind it.
- **Bookmark** = 2px vertical `--accent` line at the end of the bookmark chapter; header label "Chapter III · bookmark".
- **Sealed zone** = one column-width band after the bookmark in `--deep`, italic "sealed / never sent here". It is always exactly one band wide regardless of how many chapters remain (width MUST NOT encode remaining length).

**Right panel:** the selected reveal (kicker, Display title, quote, one-line explanation "Two threads you followed separately since chapters I and II are one person.") and a primary button "Read on to Chapter IV" → Change-chapter confirm (§8.1). Prev/next reveal arrows cycle through revealed identities.

### 6.5 Reveal moment (`Codex — 5. Reveal`)

Full-screen overlay, triggered per §8.2. Layout centred, width 960px:
1. Kicker "Chapter III · Rubric · a hidden name" (Body 21, `--accent`).
2. Connector diagram (760×124): two seals (ink-filled circles with ring) left/right, the red thread between them with a soft glow, the eye glyph at the midpoint; names under each seal (Body 23).
3. Headline (Display 70): "Lady Veris *is* the Gray Sparrow." — "is" in `--accent-hi`.
4. Quote (italic Body 24 `--dim`, max 660px).
5. Trust caption (UI 14 `--dim`): "The one passage this rests on. Without a quote, no two names are ever joined."
6. Buttons: primary filled `--ink` "Open the joined dossier"; outline "Return to The Stemma".
7. Tertiary text button: "Reveal quietly from now on" (sets a persisted preference; future reveals show as a toast instead — §8.2).
8. Backdrop: mural at full composition + radial `--accent-soft` glow centred behind the connector + dark vignette.
If multiple reveals arrive at once: pager "1 of 3" top-right of the content, `←/→` keys and buttons.
`Esc` or clicking outside closes → lands where the reader was, with the new edge highlighted for 3s.

### 6.6 Change chapter dialog (`Codex — 6. Change chapter`)

Modal, 640px wide, `--bg`, 1px `--faint` border, over a 72% black dimmer. Focus-trapped; `Esc` cancels.
1. Title (Display 42) "Where are you in the book?" + close button (44×44).
2. **Numeric input**: "I have finished chapter [ 3 ] of 4" — input 110×64, Display 40, centred. Accepts digits only; clamps to 1..N; invalid shows inline "There are only 4 chapters."
3. Helper (UI 14 `--dim`): "Type the number from your reader. Nothing is fetched until you confirm, so a mistyped 2000 can't flash anything on screen."
4. Context list: the 2 chapters before, the bookmark row (`--raise`, "current bookmark" in `--accent`), and the next row sealed. Clicking a past row fills the input.
5. "For long serials" block: arcs list (**[CONFIG DEP: arc names + ranges]**; fallback: blocks of 100 "Chapters 1–100 …"). Selecting an arc fills the input with the arc's last chapter **but only after the reader confirms** (arc names themselves can be spoilers — see §9.1 rule F6).
6. Buttons: primary "Set bookmark" (filled `--ink`, 52px), secondary "Cancel".
7. Footnote (UI 13): "Moving back seals what you had seen after that point, too."

Behaviour: no network request on typing. On confirm → §8.1.

### 6.7 States (`Codex — 7. States`)

All states use the same card language: UI 13 `--dim` state label, Display 36–40 headline, italic Body 20 `--dim` explanation, optional actions.

| State | Headline | Body | Actions |
|---|---|---|---|
| Loading | "Unclasping the codex…" | "Gathering everyone you've met up to Chapter III." + a 3-dot line glyph (ink→dim→faint; the dots fade in sequence, 1.2s loop; static under reduced motion) | — |
| Empty shelf | "No books on the shelf yet." | "Open the sample to see how it works, or add a novel of your own." | Open the sample · Add a novel |
| Error (server unreachable) | "The archive didn't answer." | "StoryWeave couldn't reach its server. Nothing was shown, and nothing past your bookmark was loaded." | Try again |
| Search no-match | "No one by that name, as of Chapter III." | "We won't say whether they ever appear. Even that would be a spoiler." | — |
| Entity not present (bookmark moved back past its first appearance) | "No one by that name, as of Chapter II." | Same neutral copy as search no-match. It MUST NOT say the name "appears later". | Go to the principal character |
| Demo data missing | "The sample book is missing." | "Run `storyweave seed-demo` to restore it." (dev-facing; only shown when API reports 0 works AND demo path configured) | — |

Error rule: on any failed fetch the UI keeps showing the **previous successfully fetched chapter's data** with a small banner "Couldn't load Chapter IV — still showing Chapter III", and the bookmark is NOT advanced. Never show partial data.

---

## 7. Graph styling (Cytoscape.js)

Implemented in `cytoscape-style.js`. Library stays **Cytoscape.js + cytoscape-cola** for the Stemma; ego graph (Dossier right panel) uses the built-in `concentric` layout; landing mini-graph uses `preset` positions from a cola pre-run or `concentric`. No library change is justified.

### 7.1 Node types (shape encodes kind; no hue coding)

| Backend type | Visual kind | Shape | Fill / border |
|---|---|---|---|
| Character | **person** | ellipse | filled `--ink`, no border |
| Organization | **order** | ellipse | fill `--bg`, 1.4px border `--ink` |
| Place | **place** | rectangle (square) | fill `--bg`, 1.4px border `--ink` |
| Item, Ability | **thing** | diamond | fill `--bg`, 1.4px border `--ink` |
| Concept, Event | *not drawn in graph by default*; listed in Dossier as "Also mentioned" | — | — |
| Title | *never drawn as a node* (titles like "Prince" are extraction noise at the view layer; show them only as part of a person's lede if linked) | — | — |

Sizes: person diameter = `clamp(16, 12 + 3·√degree, 34)` px; others fixed 16px. **Focus node**: 46px ink disk with a 60px `--bg` ring and 1.5px `--ink` outer border, showing the entity's **initial** in Pirata One 22px `--on-ink`; label in Pirata One 24px placed below-right.

Out-of-focus nodes (focus mode on): shapes and labels switch from `--ink` to `--faint`; opacity 1 (color change does the dimming — avoids muddy overlaps).

### 7.2 Labels

- EB Garamond 17px, color `--ink` (focus set) / `--faint` (others), positioned below the node (`text-valign: bottom`, margin 8px). People in roman; orders, places, things in italic (`font-style` via class).
- Text halo: `text-outline-color: --bg; text-outline-width: 3`.
- `min-zoomed-font-size: 9` so labels fade out when zoomed far out.
- Label collision: tune cola `nodeSpacing: 40`, `edgeLength: 140`; verify by screenshot at the default fit for (a) the 13-node demo and (b) a 100-node synthetic fixture.

### 7.3 Edges

| Edge kind | Style |
|---|---|
| Social tie (in focus) | straight (`curve-style: straight`, bezier for parallel), 1.4px `--dim` |
| Social tie (out of focus) | 1.2px `--line` |
| Structural (member-of, located-in) | 1px `--line`, dashed `2 4` |
| **Identity** (SECRET_IDENTITY, ALIAS, SAME_AS, REINCARNATION, TRANSMIGRATED_INTO) | 2.6px `--accent` + underlay glow (`underlay-color --accent`, `underlay-opacity 0.15`, `underlay-padding 5`). Out of focus: opacity 0.45. |

- **Parallel edges between the same pair MUST be merged** in the view model: if an identity edge exists, it absorbs any social edge between the same two nodes (the old build drew both). Other parallels: one edge, the relation list appears in the selection panel.
- No arrowheads. Direction (e.g. transmigrated *into*) is expressed in the sentence copy, not the line.
- Edge labels are **not** drawn on canvas (they were unreadable). Hover shows a tooltip (UI 13, `--panel` bg, 1px `--line`): "alias · Chapter III". Click selects and fills the right panel.

### 7.4 Relation copy mapping

| Backend relation | Dossier sentence | Kicker | Short label |
|---|---|---|---|
| SECRET_IDENTITY | "A is B." | Secret identity | secret identity |
| ALIAS / SAME_AS | "A is B." | Alias | alias |
| REINCARNATION | "A is B reborn." | Reincarnation | reincarnation |
| TRANSMIGRATED_INTO | "A now lives on as B." | Transmigration | transmigration |
| Social (ally, enemy, family, master/disciple, …) | n/a | n/a | lowercase relation ("ally of", "disciple of") |

(Exact backend enum names must be checked against `ontology.ts`; add any missing mapping with the same sentence pattern.)

### 7.5 Zoom levels

| Zoom | Behaviour |
|---|---|
| < 0.5 (overview) | Labels hidden except focus node + identity-edge endpoints; nodes shrink by 20% |
| 0.5 – 1.5 (default) | All principal labels |
| > 1.5 (close) | All labels + orders/places/things labels at full ink |
Default fit: `cy.fit(padding 60)` on focus set, not the whole graph.

### 7.6 Physics (cola)

`infinite: true` in normal motion; `animate: true`; `nodeSpacing 40`; `edgeLength 140` (identity edges 110 so revealed pairs sit closer); `convergenceThreshold 0.01`. Dragging a node pins it for the drag only. Reduced motion: `infinite: false, maxSimulationTime: 800`, then stop.

---

## 8. Interaction specs

### 8.1 Chapter control (the bookmark)

- Sources of change: Change-chapter dialog confirm; `[`/`]` keys; "Read on to Chapter N" buttons; Landing demo stepper.
- **Moving forward** (new > old):
  1. Close dialog, show inline loading state in the current view (keep old data visible under a 40% `--bg` wash).
  2. Fetch `graph?n=new` **and** (for diffing) reuse the cached `graph?n=old` payload. Never fetch any `n` > `new`.
  3. On success: commit the bookmark (state + localStorage), compute diff (new nodes, new edges, new identity edges).
  4. If the diff contains identity edges → run §8.2. Else → quiet update: new nodes/edges fade in over `--dur-slow`, "changed" tags appear in the cast list, a toast (bottom-centre, UI 14, auto-dismiss 4s): "Chapter IV · 2 new names, 3 new ties".
- **Moving backward** (new < old): fetch `graph?n=new`, replace data with no celebration; removed items fade out over `--dur-base`. Toast: "Bookmark moved back to Chapter II. Later reveals are sealed again." The client MUST drop the cached payloads for chapters > new.
- **Jumping forward far** (new − old > 10) with > 3 identity reveals: show a single summary sheet "While you were reading: 7 identities revealed" listing each as a one-line sentence with its chapter, each expandable to the full quote. Don't play 7 sequential cinematic reveals.
- Only one fetch in flight; a new confirm cancels the previous (AbortController) and the UI never shows the cancelled response.

### 8.2 Reveal moment

Trigger: forward move whose diff contains ≥1 identity edge (≤3 of them; more → summary sheet above).
Choreography (`--dur-reveal`), per reveal card:

| t (ms) | Event |
|---|---|
| 0 | Overlay fades in (200ms); page behind dims; mural brightens ≤10% |
| 200 | Both seals fade/scale in from 0.9 → 1 (200ms) |
| 400 | Red thread draws left→right between seals (500ms, `--ease-ink`), glow follows |
| 900 | Eye glyph at midpoint opens (scaleY 0 → 1, 150ms) |
| 1000 | Headline sets in (opacity + 6px rise, 250ms) |
| 1250 | Quote + caption fade in (150ms). Buttons become focusable. |

- Focus moves to the primary button when it becomes focusable; screen readers get an `aria-live="assertive"` announcement of the headline sentence.
- On close, the corresponding identity edge in Stemma/Chronicle/Dossier is highlighted for 3s (glow pulse once).
- **"Reveal quietly" preference**: reveals show as a toast with the sentence + "Read the evidence" link; no overlay.
- Reduced motion: overlay and all elements appear together with a 200ms fade.
- Replay: every identity block in the Dossier has a small "replay" icon button (aria-label "Replay this reveal") that opens the overlay for that edge (no network needed).

### 8.3 Focus mode (Stemma and ego graph)

- Click node → focus: node + 1-hop neighbourhood at full ink, rest `--faint`; camera animates (`--dur-slow`) to fit the focus set. The URL `focus` param updates.
- Click again / "Clear focus" / `Esc` → unfocus, fit all.
- Hover (no click) → temporary preview focus, reverts on mouseout (debounced 80ms).
- "Steps" control (hidden until the focus exists): 1 step (default) / 2 steps.
- Double-click node → open its dossier.
- Keyboard: `/` focuses search; arrow keys cycle through neighbours of the focus node (visible focus ring = 2px `--ink` circle around node).

### 8.4 Evidence display

- Where: Dossier identity blocks (always visible), Stemma selection panel (on edge select), Chronicle panel, Reveal card, edge hover tooltip (first 80 chars + "…").
- Format: italic EB Garamond, curly quotes, `--dim`; the chapter reference always shown with it.
- Never truncate in panels; truncate only in the tooltip.
- If a quote is missing for an identity edge in the payload (should be impossible given the citation gate), the UI MUST NOT draw the edge and should log a console warning — the UI enforces the same invariant.

### 8.5 Global keyboard map

`[` / `]` previous/next chapter (forward = confirm dialog prefilled) · `g d` Dossier · `g w` Stemma · `g c` Chronicle · `/` search · `Esc` close/unfocus · `?` shortcut sheet. Keyboard handlers are scoped to the app root, never on inputs.

---

## 9. The spoiler fence in the UI

### 9.1 Frontend fence rules (MUST)

- **F1** Only request `graph?n=k` for `k ≤ confirmed bookmark`. No prefetch of `k+1`, ever.
- **F2** Never display the number of entities, edges or reveals *beyond* the bookmark. "of N chapters" (book length) is allowed.
- **F3** The sealed zone/row is a constant size; it MUST NOT scale with remaining content.
- **F4** Search and "not yet met" messages MUST NOT confirm that a name exists later (§6.7 copy).
- **F5** On moving the bookmark back, purge cached payloads for chapters > new bookmark from memory.
- **F6** Arc/volume names are potentially spoilers: only show names of arcs whose **start** chapter ≤ bookmark; later arcs show as "Arc 4 · chapters 301–420" without a name. **[CONFIG DEP]**
- **F7** Chapter titles, if ever added, follow F6.
- **F8** Diffing for "changed" tags uses only graph(n) and graph(n−1), both fenced.
- **F9** Demo/landing mini-graph obeys F1–F3 — no hint of the upcoming reveal edge.

### 9.2 Fence line (visual)

At the bottom of the Dossier main column and as the Chronicle sealed band:
hairline — arch-door glyph (`--dim`) — italic Body 17 `--dim` copy — hairline.
Copy (Codex theme): **"The remaining leaves are sealed. Nothing past Chapter III was copied into this book."**
Hover on the glyph: tooltip "StoryWeave's server only sends chapters up to your bookmark."
"How the seal works" (landing link) opens a short explainer panel: 3 sentences + a tiny diagram "Reader → bookmark N → SQL query WHERE revealed_chapter ≤ N → only those rows leave the server". This is the engineering claim made visible for viva/demo audiences.

---

## 10. Components inventory

| Component | Variants / states |
|---|---|
| `Button` | primary (fill `--ink`, text `--on-ink`, 700), outline (1px `--ink`), quiet (text only `--dim`), icon (44×44). States: hover (`--raise` wash / fill lightens 6%), focus (2px `--ink` ring, offset 2px — never red, red stays semantic), disabled (`--faint`). Min height 44. Radius 0. |
| `Tabs` | text tabs with 1px underline for active |
| `ChapterListCompact` | read / bookmark / sealed rows |
| `ChapterDialog` | default, invalid input, loading-after-confirm |
| `CastList` | grouped, selected, "changed" tag, overflow "All N →", searchable full mode |
| `IdentityBlock` | with link / without chapter link; replay button |
| `TieRow` | — |
| `FenceLine` | dossier variant; chronicle band variant |
| `EgoGraph` | Cytoscape concentric; loading skeleton |
| `StemmaCanvas` | focus/unfocus; zoom tiers |
| `SelectionPanel` | none / node / edge |
| `ChronicleChart` | small-N columns / large-N proportional |
| `RevealOverlay` | single / paged / reduced-motion |
| `RevealSummarySheet` | for big jumps |
| `Toast` | info (update), warning (fetch failed) |
| `StateCard` | loading / empty / error / no-match |
| `Mural` + `Vignette` | per theme; web-view centre mask |
| `Tooltip` | edge hover, fence glyph |

---

## 11. Responsive & accessibility

- **≥1440**: as drawn. **1280–1439**: left rail 260, right panel 320, dossier H1 80px. **1024–1279**: right panel collapses into a toggle drawer ("Show the Stemma"); Chronicle right panel becomes a bottom sheet. **<1024**: not a target; show single column (rail becomes a top drawer) — must not break, need not be beautiful.
- Touch targets ≥ 44px. All controls are real `<button>`/`<a>`/`<input>`.
- Contrast per §4.1. Red is never the only signal (identity edges also differ in width and glow; kickers also carry text).
- Graph accessibility: an off-screen list mirror of the focused neighbourhood ("Wren — ties: Prince Caelum (secret identity, Chapter II), …") for screen readers.
- `prefers-reduced-motion` respected everywhere (§4.5).
- Language: sentence case, no ALL CAPS, no emoji.

---

## 12. Copy & voice (Codex theme strings)

Keep all theme strings in one object so themes can swap them.

| Key | Codex copy |
|---|---|
| `web` (graph tab name) | The Stemma |
| `personsHeading` | Of the Persons |
| `fence` | The remaining leaves are sealed. Nothing past Chapter {n} was copied into this book. |
| `revealKicker` | Rubric · a hidden name |
| `motto` | Written in red only where the text has earned it. |
| `thingsGroup` | Relics |
| `loading` | Unclasping the codex… |
| `lede` | first named in Chapter {c} · {k} bonds recorded |
| `landingKicker` | A spoiler-sealed companion for long serials |
| `landingH1` | Remember everyone. Spoil nothing. |

Voice: literary, calm, precise. Plain words for every action ("Change chapter", "Set bookmark", "Open dossier"). Flavour lives in headings and states, never in buttons.

---

## 13. Backend / data / config dependencies

| # | Need | Type | Status | Fallback if absent |
|---|---|---|---|---|
| D1 | Quote clause for each identity edge in the `/graph` payload | Backend (API field) | **Verify** — the citation gate stores it; confirm it is serialized in the fenced response | Hide quote; show "Evidence on file" — but prefer exposing it, it is the trust feature |
| D2 | `revealed_chapter` on every node and edge | Backend | Exists (verified live in SETUP_NOTES) | — |
| D3 | Chapter count per work | Backend | Exists (`/works` → `chapter_count`) | — |
| D4 | Entity aliases list (for search) | Backend | Verify | Search names only |
| D5 | Chapter text + clause offset for "Show it in the chapter" | Backend (new endpoint) | Likely missing | Render plain "Chapter II" text, no link |
| D6 | Arc/volume names + ranges | **Config** (`storyweave.toml`, per work) | Missing | Blocks of 100 chapters |
| D7 | Theme per work (`theme = "codex"`) | **Config** | Missing | Default to codex |
| D8 | Larger precomputed demo work (≈60–100 entities, ≥40 chapters, ≥5 staggered identity reveals, CC0 text) | **Data seed** | Missing — the 4-chapter/13-node Hollow Crown cannot demonstrate cast overload or the chapter picker | Keep Hollow Crown as a second, tiny sample |
| D9 | Relation enum list for copy mapping | Frontend (`ontology.ts`) | Exists | — |

Everything else in this spec (degree, diffs, "changed" tags, principal filter, folding) is computed client-side from fenced payloads.

---

## 14. Assets checklist

- Fonts: `@fontsource/pirata-one`, `@fontsource/eb-garamond` (400/500/600 + italic 400), `@fontsource/alegreya-sans` (400/500/700).
- `mural-codex.svg` (placeholder provided; replace with final art, same viewBox 1440×900, `preserveAspectRatio="xMidYMid slice"`).
- Icon set: 9 inline SVG glyphs (§4.4), drawn at 16/24px grid.
- Favicon: an ink seal with "S" in Pirata One on `--bg` (SVG).
- OG/share image 1200×630: landing H1 over mural (for the hosted demo).

---

## 15. Suggested build order (for the planning chat to refine)

1. **Tokens & fonts** — `tokens.css`, fontsource, base typography page. Screenshot.
2. **Shell** — mural + vignette layer, three-column layout, tabs, router, theme strings object. Screenshot at 1440 and 1280.
3. **Chapter model** — bookmark state, localStorage, Change-chapter dialog, fence rules F1–F5 with unit tests (no fetch > bookmark; cache purge on back). Test: network log at each step.
4. **Dossier** — rail, cast list, identity blocks, ties, fence line, ego graph.
5. **Stemma** — Cytoscape style from `cytoscape-style.js`, cola tuning, focus mode, selection panel, parallel-edge merge, Title/Concept/Event exclusion, principal filter.
6. **Reveal** — diffing, overlay choreography, summary sheet, quiet mode, replay.
7. **Chronicle** — small-N first, then large-N scaling.
8. **Landing & states** — try-it demo with the reveal, all state cards, error banner behaviour.
9. **Polish pass** — reduced motion, keyboard map, a11y mirror, laptop breakpoints, 100-node fixture screenshots.

Each phase: render → screenshot → compare against this spec → push.

---

## 16. Acceptance checklist (screenshot-verifiable)

- [ ] Red appears nowhere except identity edges, reveal UI, bookmark marker, "changed" tags (and optionally landing kicker).
- [ ] Pirata One never rendered below 28px.
- [ ] No uppercase letter-spaced labels anywhere.
- [ ] No mural line visible inside the Stemma canvas centre.
- [ ] Hollow Crown at ch. 2: network log shows no request with `n > 2`; Veris–Sparrow edge absent from DOM and canvas.
- [ ] Crossing ch. 2→3 plays the reveal; 3→2 does not, and shows the "sealed again" toast.
- [ ] No duplicate "Prince" node; Lady Veris–Gray Sparrow drawn as one identity edge.
- [ ] 100-node fixture at default fit: principal labels don't overlap (screenshot).
- [ ] Search for a later-chapter name at an earlier bookmark returns the neutral no-match copy.
- [ ] Every screen renders at 1280×720 without horizontal page scroll.
- [ ] Reduced-motion: no line drawing, physics stops.
