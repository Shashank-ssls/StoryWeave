import { useEffect, useState } from "react";
import Button from "../../components/Button/Button";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "../chapter/roman";
import { fetchEgo } from "../../api";
import type { EgoNeighbour } from "../../types";
import {
  IDENTITY_COPY,
  edgeLabel,
  tieLabel,
  type ViewModel,
  type VmEdge,
  type VmNode,
} from "../../graph/viewModel";
import type { Selection } from "./StemmaCanvas";
import styles from "./Stemma.module.css";

// Right selection panel (DESIGN_SPEC §6.3): none / node / edge. Evidence is never
// truncated here (§8.4) — only the canvas tooltip truncates.
//
// R7 rewrote the node case. v1's panel listed neighbours with the word "linked" and no
// evidence, which R4c's screenshots showed is not an answer to "who does X serve?". It
// now reads the `/ego` endpoint, which returns relation + grade + the verbatim sentence
// per neighbour, and splits them into what the book STATES and what is IMPLIED — the same
// distinction the solid/dashed lines draw, in words, so the two cannot disagree.

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
      {[codexTheme.legendSolid, codexTheme.legendDashed, codexTheme.legendGlow].map(([k, v]) => (
        <div key={k} className={styles.legendRow}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** One neighbour row: "serves — Lady Veris", then the sentence the book actually used. */
function EgoRow({ nb }: { nb: EgoNeighbour }): JSX.Element {
  // `outgoing` says which way round to read a directed relation: the ego endpoint gives
  // the relation as stored, so "A SERVES B" must read "commands" when B is the focus.
  const label = tieLabel(nb.relation, nb.directed && !nb.outgoing);
  return (
    <li className={styles.egoRow} data-testid="ego-row" data-entity={nb.entity_id}>
      <div className={styles.egoHead}>
        <span className={styles.egoRelation}>{label}</span>
        <span className={styles.egoName}>{nb.name}</span>
      </div>
      {nb.quote && (
        <blockquote className={styles.panelQuote} data-testid="ego-quote">
          &ldquo;{nb.quote}&rdquo;
          {nb.quote_chapter !== null && (
            <cite className={styles.egoCite}>{fillTemplate(codexTheme.quoteFrom, { n: roman(nb.quote_chapter) })}</cite>
          )}
        </blockquote>
      )}
    </li>
  );
}

function EgoList({ slug, node, n }: { slug: string; node: VmNode; n: number }): JSX.Element {
  const [rows, setRows] = useState<EgoNeighbour[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    setRows(null);
    setFailed(false);
    fetchEgo(slug, node.id, n)
      .then((r) => { if (live) setRows(r.neighbours); })
      // A 404 here means the entity is not revealed at n, which the canvas should have
      // made impossible — but the panel degrades to a message rather than an empty box.
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [slug, node.id, n]);

  if (failed) return <p className={styles.panelHint}>{codexTheme.egoFailed}</p>;
  if (rows === null) return <p className={styles.panelHint}>&nbsp;</p>;
  if (rows.length === 0) {
    return (
      <p className={styles.panelHint} data-testid="ego-empty">
        {fillTemplate(codexTheme.egoEmpty, { name: node.label, n: roman(n) })}
      </p>
    );
  }

  // Two groups, never mixed: weaker evidence is labelled as such rather than blended in.
  const stated = rows.filter((r) => r.grade !== "INFERRED");
  const implied = rows.filter((r) => r.grade === "INFERRED");
  return (
    <>
      {stated.length > 0 && (
        <>
          <div className={styles.panelSection} data-testid="ego-stated">{codexTheme.statedGroup}</div>
          <ul className={styles.egoList}>{stated.map((nb) => <EgoRow key={`${nb.entity_id}-${nb.relation}`} nb={nb} />)}</ul>
        </>
      )}
      {implied.length > 0 && (
        <>
          <div className={styles.panelSection} data-testid="ego-implied">{codexTheme.impliedGroup}</div>
          <ul className={styles.egoList}>{implied.map((nb) => <EgoRow key={`${nb.entity_id}-${nb.relation}`} nb={nb} />)}</ul>
        </>
      )}
    </>
  );
}

export default function SelectionPanel({
  vm,
  selected,
  slug,
  n,
  onOpen,
}: {
  vm: ViewModel;
  selected: Selection | null;
  slug: string;
  n: number;
  onOpen(id: string): void;
}): JSX.Element {
  if (selected?.kind === "edge") {
    const edge = vm.edges.find((e) => e.id === selected.id);
    const a = edge && vm.byId.get(edge.source);
    const b = edge && vm.byId.get(edge.target);
    if (edge && a && b) {
      const identity = edge.kind === "identity";
      return (
        <div className={styles.panel} data-testid="panel-edge" data-edge={edge.id} data-grade={edge.grade ?? "STATED"}>
          <div className={identity ? styles.kickerAccent : styles.kicker}>
            {fillTemplate(codexTheme.selectedLink, { n: roman(edge.revealed_chapter) })}
          </div>
          <h2 className={styles.panelTitle}>
            {identity ? identitySentence(edge, vm).replace(/\.$/, "") : fillTemplate(codexTheme.socialTitle, { a: a.label, b: b.label })}
          </h2>
          {/* R7: the relation is named on every edge, identity or not, in the same plain
              words the line carries — "(implied)" included, so the panel and the dashes
              always agree about how strong the evidence is. */}
          <div className={styles.panelMeta} data-testid="panel-relation">{edgeLabel(edge)}</div>
          {edge.quote && (
            <blockquote className={styles.panelQuote} data-testid="panel-quote">
              &ldquo;{edge.quote}&rdquo;
              {edge.quoteChapter !== null && (
                <cite className={styles.egoCite}>{fillTemplate(codexTheme.quoteFrom, { n: roman(edge.quoteChapter) })}</cite>
              )}
            </blockquote>
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
      return (
        <div className={styles.panel} data-testid="panel-node" data-entity={node.id}>
          <h2 className={styles.panelTitle}>{node.label}</h2>
          <div className={styles.panelMeta}>
            {fillTemplate(codexTheme.selectedName, { type: kindName(node), n: roman(node.first_seen_chapter) })}
          </div>
          <EgoList slug={slug} node={node} n={n} />
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
