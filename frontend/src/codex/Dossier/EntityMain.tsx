import { useState } from "react";
import Ornament from "../../components/Ornament/Ornament";
import { EyeIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "../chapter/roman";
import { countWords, IDENTITY_COPY, tieLabel, tiesOf, type ViewModel, type VmNode } from "../../graph/viewModel";
import styles from "./Dossier.module.css";

// Dossier main column content (DESIGN_SPEC §6.2 Main items 2-6, §8.4 evidence):
// H1, lede, one ornament, identity blocks (newest reveal first), ties grid, "Also
// mentioned". The fence line (item 8) is rendered by the parent so it pins to the bottom.

const TIES_TOP = 12;

export default function EntityMain({
  vm,
  entity,
  onOpen,
}: {
  vm: ViewModel;
  entity: VmNode;
  onOpen(id: string): void;
}): JSX.Element {
  const [allTies, setAllTies] = useState(false);
  const ties = tiesOf(vm, entity.id);

  const identity = ties
    .filter((t) => t.edge.kind === "identity")
    .sort((a, b) => b.edge.revealed_chapter - a.edge.revealed_chapter);
  const social = ties
    .filter((t) => t.edge.kind !== "identity")
    .sort((a, b) => a.edge.revealed_chapter - b.edge.revealed_chapter || a.other.label.localeCompare(b.other.label));
  const shownTies = allTies ? social : social.slice(0, TIES_TOP);

  const link = (n: VmNode, cls: string | undefined): JSX.Element => (
    <button type="button" className={cls} onClick={() => onOpen(n.id)} data-entity={n.id}>
      {n.label}
    </button>
  );

  return (
    <article className={styles.entity} data-testid="entity-main" data-entity={entity.id}>
      <h1 className={styles.h1} data-testid="entity-h1">{entity.label}</h1>
      <p className={styles.lede} data-testid="entity-lede">
        {ties.length === 1
          ? fillTemplate(codexTheme.ledeOne, { c: roman(entity.first_seen_chapter) })
          : fillTemplate(codexTheme.lede, { c: roman(entity.first_seen_chapter), k: countWords(ties.length) })}
      </p>
      <div className={styles.ornament}>
        <Ornament />
      </div>

      {identity.map(({ edge, other }) => {
        const copy = IDENTITY_COPY[edge.relation] ?? IDENTITY_COPY.ALIAS!;
        // Sentence in source→target order (§7.4; the line has no arrowhead, the copy
        // carries direction). Whichever end is "the other" is the italic red link.
        const aIsEntity = edge.source === entity.id;
        const [a, b] = aIsEntity ? [entity, other] : [other, entity];
        const parts = copy.sentence.split(/(\{a\}|\{b\})/);
        return (
          <section key={edge.id} className={styles.identity} data-testid="identity-block" data-edge={edge.id} data-relation={edge.relation}>
            <EyeIcon size={24} className={styles.eye} />
            <div className={styles.identityBody}>
              <div className={styles.kicker}>
                {fillTemplate(codexTheme.revealedIn, { kicker: copy.kicker, n: roman(edge.revealed_chapter) })}
              </div>
              <p className={styles.sentence}>
                {parts.map((p, i) => {
                  if (p === "{a}") return a.id === entity.id ? <span key={i}>{a.label}</span> : <span key={i}>{link(a, styles.otherName)}</span>;
                  if (p === "{b}") return b.id === entity.id ? <span key={i}>{b.label}</span> : <span key={i}>{link(b, styles.otherName)}</span>;
                  return <span key={i}>{p}</span>;
                })}
              </p>
              {/* §8.4: never truncated in a panel; curly quotes; chapter always shown. */}
              <blockquote className={styles.quote} data-testid="identity-quote">
                “{edge.evidence_span}”
              </blockquote>
              {/* D5 (chapter text + offset) is absent → plain "Chapter N", no link (§6.2 item 5). */}
              <div className={styles.quoteSource}>{fillTemplate(codexTheme.chapter, { n: roman(edge.revealed_chapter) })}</div>
            </div>
          </section>
        );
      })}

      {social.length > 0 && (
        <ul className={styles.ties} data-testid="ties">
          {shownTies.map(({ edge, other }) => (
            <li key={edge.id} className={styles.tie} data-testid="tie" data-edge={edge.id} data-entity={other.id}>
              {link(other, styles.tieName)}
              <span className={styles.tieMeta}>
                {fillTemplate(codexTheme.tie, { rel: tieLabel(edge.relation), n: roman(edge.revealed_chapter) })}
              </span>
            </li>
          ))}
        </ul>
      )}
      {social.length > TIES_TOP && !allTies && (
        <button type="button" className={styles.moreLink} onClick={() => setAllTies(true)} data-testid="ties-all">
          {fillTemplate(codexTheme.allTies, { n: social.length })}
        </button>
      )}

      {vm.alsoMentioned.length > 0 && (
        <p className={styles.alsoMentioned} data-testid="also-mentioned">
          {codexTheme.alsoMentioned}: {vm.alsoMentioned.map((n) => n.label).join(" · ")}
        </p>
      )}
    </article>
  );
}
