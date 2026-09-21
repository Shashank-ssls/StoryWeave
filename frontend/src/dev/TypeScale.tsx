import { useEffect, useState } from "react";
import Button from "../components/Button/Button";
import Tabs from "../components/Tabs/Tabs";
import Input from "../components/Input/Input";
import Ornament from "../components/Ornament/Ornament";
import {
  ArchDoorIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CloseIcon,
  EyeIcon,
  LockIcon,
  MinusIcon,
  PlusIcon,
  ReplayIcon,
  SearchIcon,
  type IconProps,
} from "../icons";
import { readRevealQuiet, writeRevealQuiet } from "../codex/reveal/revealPrefs";
import "./TypeScale.css";

// The hidden #/_type dev route (FRONTEND_OVERHAUL.md §5 Phase 1 / R1): every token and
// primitive in one place, so a phase can be screenshot-verified against DESIGN_SPEC.md
// §4 before any real screen exists. R2 replaces the hash check in main.tsx with the real
// router; this page itself is expected to persist as the design-system reference.

// DESIGN_SPEC.md §4.2 type scale (px). Display (Pirata One) is never shown below 28px —
// that's a hard rule (§2 rule 5), not just a style choice, so the scale below simply omits
// the Display sample for sizes under 28.
const TYPE_SCALE = [13, 14, 16, 18, 21, 24, 30, 36, 44, 60, 72, 96];

// DESIGN_SPEC.md §4.1 — every color token in tokens.css. Values are read back from the
// live stylesheet via getComputedStyle (never hardcoded here) so this page can never drift
// out of sync with tokens.css, and so it never needs a raw-hex exemption of its own.
const COLOR_TOKENS: { name: string; role: string }[] = [
  { name: "--bg", role: "App background" },
  { name: "--deep", role: "Inputs, sealed zones, deepest wells" },
  { name: "--panel", role: "Side rails and panels over the mural" },
  { name: "--raise", role: "Selected list row, hover wash" },
  { name: "--line", role: "Hairlines, borders, dividers" },
  { name: "--ink", role: "Primary text, primary node fill" },
  { name: "--dim", role: "Secondary text, near edges" },
  { name: "--faint", role: "Tertiary text, faded/sealed text" },
  { name: "--mural", role: "Mural line-art stroke only" },
  { name: "--accent", role: "Rubric red — reveals only" },
  { name: "--accent-hi", role: "Emphasised word inside a reveal" },
  { name: "--accent-soft", role: "Glow halos, reveal backdrop tint" },
  { name: "--on-ink", role: "Text on --ink fills" },
  { name: "--scrim", role: "Dialog/reveal backdrop dimmer" },
];

const ICON_LIST: { name: string; Glyph: (p: IconProps) => JSX.Element }[] = [
  { name: "chevron-left", Glyph: ChevronLeftIcon },
  { name: "chevron-right", Glyph: ChevronRightIcon },
  { name: "close", Glyph: CloseIcon },
  { name: "lock", Glyph: LockIcon },
  { name: "arch-door", Glyph: ArchDoorIcon },
  { name: "eye", Glyph: EyeIcon },
  { name: "plus", Glyph: PlusIcon },
  { name: "minus", Glyph: MinusIcon },
  { name: "search", Glyph: SearchIcon },
  { name: "replay", Glyph: ReplayIcon },
];

function useTokenValue(name: string): string {
  const [value, setValue] = useState("");
  useEffect(() => {
    setValue(getComputedStyle(document.documentElement).getPropertyValue(name).trim());
  }, [name]);
  return value;
}

// `tok-*` prefix deliberately avoids the old app's own (unrelated) `.swatch` class in
// styles.css — both stylesheets load globally (no CSS Modules), and `.swatch` there is a
// 9px legend dot with border-radius:50%, which silently clobbered this before the rename.
function Swatch({ name, role }: { name: string; role: string }): JSX.Element {
  const value = useTokenValue(name);
  return (
    <div className="tok-swatch" data-testid={`swatch-${name}`}>
      <div className="tok-swatch-box" style={{ background: `var(${name})` }} />
      <div className="tok-swatch-name">{name}</div>
      <div className="tok-swatch-value">{value}</div>
      <div className="tok-swatch-role">{role}</div>
    </div>
  );
}

function TypeRow({ size }: { size: number }): JSX.Element {
  const showDisplay = size >= 28;
  return (
    <div className="type-row" data-testid={`type-row-${size}`}>
      <div className="type-row-size">{size}px</div>
      <div className="type-samples">
        {showDisplay && (
          <div
            className="type-sample"
            style={{ fontFamily: "var(--font-display)", fontSize: size, lineHeight: "var(--lh-display)" }}
          >
            The Hollow Crown · Pirata One {size} / display
          </div>
        )}
        <div
          className="type-sample"
          style={{ fontFamily: "var(--font-body)", fontSize: size, lineHeight: "var(--lh-body)" }}
        >
          Wren is Prince Caelum · EB Garamond {size} / body
        </div>
        <div
          className="type-sample"
          style={{ fontFamily: "var(--font-ui)", fontSize: size }}
        >
          Change chapter · Alegreya Sans {size} / ui
        </div>
      </div>
    </div>
  );
}

const TAB_ITEMS = [
  { key: "dossier", label: "Dossier" },
  { key: "web", label: "The Stemma" },
  { key: "chronicle", label: "Chronicle" },
];

export default function TypeScale(): JSX.Element {
  const [activeTab, setActiveTab] = useState("dossier");
  const [quiet, setQuiet] = useState(() => readRevealQuiet());

  return (
    <div className="type-page">
      <header className="type-header">
        <h1 className="type-page-title">Design tokens — #/_type</h1>
        <p className="type-page-note">
          Hidden dev route (R1). R2 replaces this hash check with the real router; this
          page persists as the design-system reference.
        </p>
      </header>

      <section aria-labelledby="type-scale-heading">
        <h2 id="type-scale-heading" className="type-section-title">
          Type scale
        </h2>
        {TYPE_SCALE.map((size) => (
          <TypeRow key={size} size={size} />
        ))}
      </section>

      <section aria-labelledby="colors-heading">
        <h2 id="colors-heading" className="type-section-title">
          Color tokens
        </h2>
        <div className="tok-swatch-grid">
          {COLOR_TOKENS.map((t) => (
            <Swatch key={t.name} name={t.name} role={t.role} />
          ))}
        </div>
      </section>

      <section aria-labelledby="buttons-heading">
        <h2 id="buttons-heading" className="type-section-title">
          Buttons
        </h2>
        <div className="primitive-row">
          <Button variant="primary" data-testid="btn-primary-default">
            Set bookmark
          </Button>
          <Button variant="primary" disabled data-testid="btn-primary-disabled">
            Set bookmark
          </Button>
          <Button variant="outline" data-testid="btn-outline-default">
            Cancel
          </Button>
          <Button variant="outline" disabled data-testid="btn-outline-disabled">
            Cancel
          </Button>
          <Button variant="quiet" data-testid="btn-quiet-default">
            Reveal quietly from now on
          </Button>
          <Button variant="quiet" disabled data-testid="btn-quiet-disabled">
            Reveal quietly from now on
          </Button>
          <Button variant="icon" aria-label="Close" data-testid="btn-icon-default">
            <CloseIcon />
          </Button>
          <Button variant="icon" aria-label="Close" disabled data-testid="btn-icon-disabled">
            <CloseIcon />
          </Button>
        </div>
      </section>

      <section aria-labelledby="tabs-heading">
        <h2 id="tabs-heading" className="type-section-title">
          Tabs
        </h2>
        <Tabs items={TAB_ITEMS} activeKey={activeTab} onChange={setActiveTab} aria-label="Screen tabs demo" />
      </section>

      <section aria-labelledby="input-heading">
        <h2 id="input-heading" className="type-section-title">
          Input
        </h2>
        <div className="primitive-row">
          <Input placeholder="name or alias" data-testid="input-empty" />
          <Input defaultValue="Wren" data-testid="input-filled" />
          <Input defaultValue="Wren" disabled data-testid="input-disabled" />
        </div>
      </section>

      <section aria-labelledby="ornament-heading">
        <h2 id="ornament-heading" className="type-section-title">
          Ornament rule
        </h2>
        <Ornament />
      </section>

      <section aria-labelledby="reveal-heading">
        <h2 id="reveal-heading" className="type-section-title">
          Reveal preference (R6)
        </h2>
        <label className="primitive-row">
          <input
            type="checkbox"
            checked={quiet}
            onChange={(e) => {
              writeRevealQuiet(e.target.checked);
              setQuiet(e.target.checked);
            }}
            data-testid="type-quiet-toggle"
          />
          Reveal quietly from now on (storyweave:revealQuiet)
        </label>
      </section>

      <section aria-labelledby="icons-heading">
        <h2 id="icons-heading" className="type-section-title">
          Icons
        </h2>
        <div className="icon-grid">
          {ICON_LIST.map(({ name, Glyph }) => (
            <div className="icon-cell" key={name}>
              <Glyph size={16} />
              <Glyph size={24} />
              <span className="icon-name">{name}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
