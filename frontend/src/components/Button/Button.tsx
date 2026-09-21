import type { ButtonHTMLAttributes } from "react";
import "./Button.css";

export type ButtonVariant = "primary" | "outline" | "quiet" | "icon";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

// DESIGN_SPEC.md §10 Button: primary / outline / quiet / icon, 44px min target, radius 0.
// Hover/focus/disabled all come from tokens.css (--raise wash, the global :focus-visible
// ring, --faint) — nothing here is a one-off color, per the tokens-only rule.
export default function Button({
  variant = "primary",
  className,
  type = "button",
  ...rest
}: Props): JSX.Element {
  const cls = ["btn", `btn-${variant}`, className].filter(Boolean).join(" ");
  return <button type={type} className={cls} {...rest} />;
}
