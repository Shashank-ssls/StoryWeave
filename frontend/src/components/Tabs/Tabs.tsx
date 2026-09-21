import "./Tabs.css";

export interface TabItem {
  key: string;
  label: string;
}

interface Props {
  items: TabItem[];
  activeKey: string;
  onChange: (key: string) => void;
  "aria-label"?: string;
}

// DESIGN_SPEC.md §10 Tabs: text tabs, 1px underline for the active one, --dim otherwise.
export default function Tabs({ items, activeKey, onChange, ...rest }: Props): JSX.Element {
  return (
    <div className="tabs" role="tablist" {...rest}>
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          role="tab"
          className="tab"
          aria-selected={item.key === activeKey}
          onClick={() => onChange(item.key)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
