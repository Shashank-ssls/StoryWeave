import { useMemo, useState } from "react";
import Input from "../../components/Input/Input";
import { codexTheme, fillTemplate } from "../theme";
import { sortCast, type ViewModel, type VmNode } from "../../graph/viewModel";
import styles from "./Dossier.module.css";

// Dramatis Personae (DESIGN_SPEC §6.2 rail item 3): people sorted by degree then first
// appearance, "changed" tags (F8 diff, computed upstream), then the two inline groups.
// Overflow: top 12 people + "All N people →" which opens a searchable full list here in
// the rail. Every name is a real button that opens its dossier.

const TOP = 12;

export default function CastList({
  vm,
  selectedId,
  changed,
  onOpen,
}: {
  vm: ViewModel;
  selectedId: string | null;
  changed: Set<string>;
  onOpen(id: string): void;
}): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState("");

  const people = useMemo(() => sortCast(vm.nodes.filter((n) => n.kind === "person")), [vm]);
  const orders = useMemo(() => sortCast(vm.nodes.filter((n) => n.kind === "order")), [vm]);
  const placesRelics = useMemo(
    () => sortCast(vm.nodes.filter((n) => n.kind === "place" || n.kind === "thing")),
    [vm],
  );

  const overflow = people.length > TOP;
  const q = query.trim().toLowerCase();
  // Search (D4 fallback per R0: every alias is its own fenced node, so label search is
  // the full feature). Only names already in the fenced payload can ever match (F4).
  const shown = expanded && overflow ? (q ? people.filter((p) => p.label.toLowerCase().includes(q)) : people) : people.slice(0, TOP);

  const row = (n: VmNode): JSX.Element => (
    <li key={n.id}>
      <button
        type="button"
        className={`${styles.castRow} ${n.id === selectedId ? styles.castSelected : ""}`}
        onClick={() => onOpen(n.id)}
        aria-current={n.id === selectedId ? "page" : undefined}
        data-testid="cast-row"
        data-entity={n.id}
      >
        <span>{n.label}</span>
        {changed.has(n.id) && <span className={styles.changedTag} data-testid="changed-tag">{codexTheme.changed}</span>}
      </button>
    </li>
  );

  const inline = (nodes: VmNode[]): JSX.Element => (
    <p className={styles.groupLine}>
      {nodes.map((n, i) => (
        <span key={n.id}>
          {i > 0 && <span className={styles.sep}> · </span>}
          <button type="button" className={styles.groupLink} onClick={() => onOpen(n.id)} data-testid="cast-group-item" data-entity={n.id}>
            {n.label}
          </button>
        </span>
      ))}
    </p>
  );

  return (
    <nav className={styles.cast} aria-label={codexTheme.dramatisPersonae} data-testid="cast">
      <h3 className={styles.castHeader}>{codexTheme.dramatisPersonae}</h3>
      {expanded && overflow && (
        <Input
          className={styles.castSearch}
          placeholder={codexTheme.findName}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label={codexTheme.findName}
          data-testid="cast-search"
        />
      )}
      <ul className={styles.castList} data-testid="cast-people">
        {shown.map(row)}
      </ul>
      {overflow && !expanded && (
        <button type="button" className={styles.moreLink} onClick={() => setExpanded(true)} data-testid="cast-all">
          {fillTemplate(codexTheme.allPeople, { n: people.length })}
        </button>
      )}
      {orders.length > 0 && (
        <>
          <h4 className={styles.groupHeader}>{codexTheme.ordersGroup}</h4>
          {inline(orders)}
        </>
      )}
      {placesRelics.length > 0 && (
        <>
          <h4 className={styles.groupHeader}>{codexTheme.placesGroup}</h4>
          {inline(placesRelics)}
        </>
      )}
    </nav>
  );
}
