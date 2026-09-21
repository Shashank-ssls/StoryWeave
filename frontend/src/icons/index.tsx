// The Codex icon set (DESIGN_SPEC.md §4.4): inline stroke SVG, square caps, currentColor.
// No emoji, no filled icon packs. Colour is deliberately left to the caller via
// `currentColor` (CSS `color`) — the eye glyph is `--accent` only where the spec's red
// discipline permits it (identity/reveal contexts), never baked into the primitive itself.

import type { ReactNode } from "react";

export interface IconProps {
  size?: 16 | 24;
  className?: string;
}

function Svg({
  size = 24,
  className,
  children,
}: IconProps & { children: ReactNode }): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="square"
      strokeLinejoin="miter"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export function ChevronLeftIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <polyline points="15 4 9 12 15 20" />
    </Svg>
  );
}

export function ChevronRightIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <polyline points="9 4 15 12 9 20" />
    </Svg>
  );
}

export function CloseIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <line x1="5" y1="5" x2="19" y2="19" />
      <line x1="19" y1="5" x2="5" y2="19" />
    </Svg>
  );
}

export function LockIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <rect x="5" y="11" width="14" height="9" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </Svg>
  );
}

export function ArchDoorIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <path d="M6 21V11a6 6 0 0 1 12 0v10" />
      <line x1="6" y1="21" x2="18" y2="21" />
    </Svg>
  );
}

export function EyeIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  );
}

export function PlusIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </Svg>
  );
}

export function MinusIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <line x1="5" y1="12" x2="19" y2="12" />
    </Svg>
  );
}

export function SearchIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <circle cx="10" cy="10" r="6" />
      <line x1="20" y1="20" x2="14.5" y2="14.5" />
    </Svg>
  );
}

// R6 addition (DESIGN_SPEC §8.2 replay button): not in the original §4.4/§14 icon
// checklist, which predates the reveal moment's own replay affordance. Same stroke
// language as the rest of the set (1.5px, square caps, currentColor).
export function ReplayIcon(props: IconProps): JSX.Element {
  return (
    <Svg {...props}>
      <path d="M4 12a8 8 0 1 1 2.6 5.9" />
      <polyline points="4 17 4 12 9 12" />
    </Svg>
  );
}

export const ICONS = {
  "chevron-left": ChevronLeftIcon,
  "chevron-right": ChevronRightIcon,
  close: CloseIcon,
  lock: LockIcon,
  "arch-door": ArchDoorIcon,
  eye: EyeIcon,
  plus: PlusIcon,
  minus: MinusIcon,
  search: SearchIcon,
  replay: ReplayIcon,
} as const;
