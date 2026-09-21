import type { InputHTMLAttributes } from "react";
import "./Input.css";

type Props = InputHTMLAttributes<HTMLInputElement>;

// Text input primitive: --deep well, 1px --line border, 44px min height, radius 0.
// Not an explicit §10 row, but every screen that needs one (search, chapter number) uses
// this same shape — see DESIGN_SPEC.md §6.3/§6.6.
export default function Input({ className, ...rest }: Props): JSX.Element {
  const cls = ["input", className].filter(Boolean).join(" ");
  return <input className={cls} {...rest} />;
}
