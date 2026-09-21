import Button from "../../components/Button/Button";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "../chapter/roman";
import { IDENTITY_COPY, tieLabel, tiesOf, type ViewModel, type VmEdge, type VmNode } from "../../graph/viewModel";
import type { Selection } from "./StemmaCanvas";
import styles from "./Stemma.module.css";

// Right selection panel (DESIGN_SPEC §6.3): none / node / edge. Evidence is never
// truncated here (§8.4) — only the canvas tooltip truncates.

function kindName(n: VmNode): string {
  return n.kind === "person" ? codexTheme.kindPerson : n.kind === "order" ? codexTheme.kindOrder : n.kind === "place" ? codexTheme.kindPlace : codexTheme.kindThing;
}

export function identitySentence(edge: VmEdge, vm: ViewModel): string {
  const copy = IDENTITY_COPY[edge.relation] ?? IDENTITY_COPY.ALIAS!;
  const a = vm.byId.get(edge.source)?.label ?? "";
  const b = vm.byId.get(edge.target)?.label ?? "";
  return copy.sentence.replace("{a}", a).replace("{b}", b);
}

function Legend(): JSX.Element {
  return (
    <dl className={styles.legend} data-testid="panel-legend">
      {[codexTheme.legendSolid, codexTheme.legendGlow, codexTheme.legendFaded].map(([k, v]) => (
        <div key={k} className={styles.legendRow}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function SelectionPanel({
  vm,
  selected,
  onOpen,
}: {
  vm: ViewModel;
  selected: Selection | null;
  onOpen(id: string): void;
}): JSX.Element {
  if (selected?.kind === "edge") {
    const edge = vm.edges.find((e) => e.id === selected.id);
    const a = edge && vm.byId.get(edge.source);
    const b = edge && vm.byId.get(edge.target);
    if (edge && a && b) {
      const identity = edge.kind === "identity";
      return (
        <div className={styles.panel} data-testid="panel-edge" data-edge={edge.id}>
          <div className={identity ? styles.kickerAccent : styles.kicker}>
            {fillTemplate(codexTheme.selectedLink, { n: roman(edge.revealed_chapter) })}
          </div>
          <h2 className={styles.panelTitle}>
            {identity ? identitySentence(edge, vm).replace(/\.$/, "") : fillTemplate(codexTheme.socialTitle, { a: a.label, b: b.label })}
          </h2>
          {!identity && <div className={styles.panelMeta}>{tieLabel(edge.relation)}</div>}
          {identity && edge.evidence_span && (
            <blockquote className={styles.panelQuote} data-testid="panel-quote">“{edge.evidence_span}”</blockquote>
          )}
          <hr className={styles.hairline} />
          <Legend />
          <div className={styles.panelSpacer} />
          <Button variant="outline" className={styles.panelButton} onClick={() => onOpen(a.id)} data-testid="panel-open">
            {fillTemplate(codexTheme.openDossierOf, { name: a.label })}
          </Button>
        </div>
      );
    }
  }

  if (selected?.kind === "node") {
    const node = vm.byId.get(selected.id);
    if (node) {
      const ties = tiesOf(vm, node.id);
      const identity = ties.filter((t) => t.edge.kind === "identity");
      const social = ties.filter((t) => t.edge.kind !== "identity").sort((x, y) => y.other.degree - x.other.degree).slice(0, 5);
      return (
        <div className={styles.panel} data-testid="panel-node" data-entity={node.id}>
          <h2 className={styles.panelTitle}>{node.label}</h2>
          <div className={styles.panelMeta}>
            {fillTemplate(codexTheme.selectedName, { type: kindName(node), n: roman(node.first_seen_chapter) })}
          </div>
          {identity.map(({ edge }) => (
            <p key={edge.id} className={styles.panelIdentity} data-testid="panel-identity">
              {identitySentence(edge, vm)}
            </p>
          ))}
          {social.length > 0 && (
            <>
              <div className={styles.panelSection}>{codexTheme.topTies}</div>
              <ul className={styles.panelTies}>
                {social.map(({ edge, other }) => (
                  <li key={edge.id} className={styles.panelTie}>
                    <span>{other.label}</span>
                    <span className={styles.panelTieMeta}>{fillTemplate(codexTheme.tie, { rel: tieLabel(edge.relation), n: roman(edge.revealed_chapter) })}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          <div className={styles.panelSpacer} />
          <Button variant="outline" className={styles.panelButton} onClick={() => onOpen(node.id)} data-testid="panel-open">
            {fillTemplate(codexTheme.openDossierOf, { name: node.label })}
          </Button>
        </div>
      );
    }
  }

  return (
    <div className={styles.panel} data-testid="panel-none">
      <Legend />
      <p className={styles.panelHint}>{codexTheme.panelHint}</p>
    </div>
  );
}
