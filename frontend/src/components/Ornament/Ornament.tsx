import "./Ornament.css";

interface Props {
  width?: number;
}

// DESIGN_SPEC.md §4.4 section ornament rule: a thin line with a small centred lozenge.
// Used once per page under the H1 — never stacked.
export default function Ornament({ width = 480 }: Props): JSX.Element {
  return <div className="ornament" role="presentation" style={{ width, maxWidth: "100%" }} />;
}
