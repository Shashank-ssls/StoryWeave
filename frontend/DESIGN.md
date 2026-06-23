# StoryWeave — frontend design system (Phase 8 rebuild)

> The token pass (skill: brainstorm → critique → build). Every color/type/layout
> decision below is derived here and the code follows it exactly.

## Subject & thesis
StoryWeave maps what a *reader* knows at chapter N — characters, places, and the
secret identities a story discloses over time. The defining act is a **reveal**: a
hidden link igniting once the text earns it (Wren *is* Caelum at ch2).

**Thesis — "a constellation that ignites as you read."** The graph is a night sky;
entities are luminous points colored by kind; advancing the chapter slider lights up
new stars and, at a reveal, **ignites a golden identity filament between two stars.**
Calm sky, one bright act. That single act is where the boldness is spent.

## Color (hex — Cytoscape's canvas needs real colors, not oklch)
- `--ground` **#0b0d14** — midnight (not pure black; a touch of indigo)
- `--surface` **#141828** — panels/overlays
- `--line` **#272c40** — hairlines, borders
- `--ink` **#e9e4d6** — parchment text
- `--ink-dim` **#8b91a8** — secondary text
- `--reveal` **#ffd073** — GOLD, reserved for identity reveals + the bloom + the live brand accent. Semantic, never decorative.

**The 8-type constellation** (distinct hues, harmonized luminance, legible on midnight):
Character `#7aa2f7` · Place `#63d29a` · Organization `#e36873` · Item `#d8a24a` ·
Ability `#b58cf0` · Concept `#46c7d8` · Event `#ee8b49` · Title `#de85c2`.
The legend renders these exact hex values; the graph uses the same map. No grey nodes.

## Type (deliberate pairing, bundled offline via @fontsource — not a system stack)
- **Display — Spectral** (literary serif): wordmark, work titles, entity names in panels. Evokes a printed novel.
- **Body/UI — IBM Plex Sans**: controls, legend, readouts, graph node labels (legible at small canvas sizes).
- **Data — IBM Plex Mono**: chapter numbers, counts, provenance (`via llm`).
- Scale: 12 / 13 / 15 / 18 / 22 / 30 / 44. Display weights 400/500; body 400/500/600.

## Layout
```
┌───────────────────────────────────────────────────────────────┐
│ ✦ StoryWeave   The Hollow Crown            ch 4 · 13 ✦ · 13 ⌁  │  top bar (quiet)
├───────────────────────────────────────────────────────────────┤
│                                                                 │
│            · · the constellation (full-bleed) · ·               │  graph canvas
│        drag a star → neighbours react → it re-settles           │
│        hover → focus a star + its links, dim the rest           │
│                                            ┌─ detail ─┐         │
│  ┌─ legend ─┐                              │ Caelum    │         │
│  │ ● types  │                              │ SECRET…   │         │
│  └──────────┘                              └───────────┘         │
├───────────────────────────────────────────────────────────────┤
│ Reading position  ●━━━━━━━━━━━━━━━━━━━━━━━━━━○        ch 4 / 4   │  timeline slider
└───────────────────────────────────────────────────────────────┘
```
First load shows a brief **cover** (product + work + what the slider does + "Enter"),
so no one is dropped into an unexplained graph.

## Motion / physics
- **Engine: cytoscape-cola** (continuous constraint physics). Justified over fcose
  (static, no live reaction) and d3-force (needs hand-wiring to Cytoscape's renderer):
  cola keeps simulating, so dragging a node makes neighbours react elastically and the
  graph re-settles — the Obsidian feel the brief specifies.
- **Hover-focus:** highlight a node + its 1-hop neighbourhood and their edges; dim the rest.
- **Edges encode tier:** Tier-1 structural = thin/quiet hairline; Tier-2 social = medium;
  Tier-3 identity = the bold **gold** filament, label shown on hover/select.
- **The signature (bloom):** crossing a reveal chapter ignites the new identity edge —
  it draws in with a brief gold glow + width pulse and its relation label fades in.
- **Reduced motion:** physics runs finite (settle once, stop) and the bloom becomes a
  plain appear — calm, not broken.

## Labels (the old build's worst failure)
- Node labels render below the node with a **text halo** (outline = ground colour) so
  they read over edges; `min-zoomed-font-size` fades them when zoomed out.
- cola spacing (node separation + edge length) is tuned so labels don't collide at the
  default fit; on hover the focused labels brighten. Verified by screenshot, not assumed.

## Self-critique vs the three AI defaults
"Near-black + one bright accent" is AI-default #2 — this risks drifting there. How this
is a *choice*, not the default: (1) the accent gold is **semantic** (only reveals), not
ambient; the everyday palette is an 8-hue constellation, not a monochrome + acid pop.
(2) Type is a **Spectral × Plex** literary/technical pairing, not Inter/system. (3) The
slider is reframed as a **reading timeline**, and the one bold moment (the ignite) is
**tied to the data** (the reveal chapter), not decoration. Risk taken: a live physics sky
you can disturb. Everything else stays quiet.
```
