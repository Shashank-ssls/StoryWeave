import { useEffect, useState } from "react";
import { PENDING_ENTITY, navigate, routePath, type WorkRoute } from "../../router/useHashRoute";
import { useWorkTitle } from "../useWorkTitle";
import Tabs from "../../components/Tabs/Tabs";
import Button from "../../components/Button/Button";
import { ArchDoorIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { tabItems, navigateToTab } from "../tabs";
import { roman } from "../chapter/roman";
import { useChapter } from "../chapter/ChapterProvider";
import ChapterListCompact from "../chapter/ChapterListCompact";
import StateCard from "../states/StateCard";
import { useDossier } from "./useDossier";
import CastList from "./CastList";
import EntityMain from "./EntityMain";
import EgoGraph from "./EgoGraph";
import styles from "./Dossier.module.css";

// DESIGN_SPEC.md §6.2 Dossier — the primary screen. Three columns: rail (wordmark, title,
// chapter block, cast), main (entity), right panel (ego graph). Every piece of story data
// on this screen comes from the R3 chapter model's fenced payload for the bookmark (and,
// for "changed" tags only, the fenced n−1 payload) — nothing here fetches.
export default function Dossier({ route }: { route: WorkRoute }): JSX.Element {
  const title = useWorkTitle();
  const m = useChapter();
  const { vm, principal, changed } = useDossier();
  const entityId = route.name === "work-entity" ? route.entityId : PENDING_ENTITY;
  // R9 §11: 1024-1279 the right panel is a toggle drawer; <1024 the rail is a top drawer
  // too (CSS media queries do the actual layout switch; these just gate whether the
  // drawer classes apply, since the toggles themselves are display:none outside range).
  const [panelOpen, setPanelOpen] = useState(false);
  const [railOpen, setRailOpen] = useState(false);
  useEffect(() => {
    if (!panelOpen && !railOpen) return;
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") { setPanelOpen(false); setRailOpen(false); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panelOpen, railOpen]);

  // `#/work/:slug` (no entity) → the principal character at the current bookmark (P1).
  // location.replace: no history entry, but hashchange still fires so the router follows.
  useEffect(() => {
    if (entityId === PENDING_ENTITY && principal) {
      window.location.replace(routePath({ name: "work-entity", slug: route.slug, entityId: principal.id }));
    }
  }, [entityId, principal, route.slug]);

  const open = (id: string): void => navigate({ name: "work-entity", slug: route.slug, entityId: id });
  const entity = vm && entityId !== PENDING_ENTITY ? (vm.byId.get(entityId) ?? null) : null;

  const failedWithNothing = m.data === null && (m.banner !== null || m.workError);

  return (
    <div className={styles.dossier} data-testid="dossier-root">
      <aside className={`${styles.rail} ${railOpen ? styles.railOpen : ""}`} data-testid="dossier-rail">
        <a className={styles.wordmark} href={routePath({ name: "landing" })}>StoryWeave</a>
        <div className={styles.novelTitle}>{title}</div>
        <ChapterListCompact />
        {vm && <CastList vm={vm} selectedId={entity?.id ?? null} changed={changed} onOpen={open} />}
      </aside>

      <main className={styles.main}>
        <div className={styles.topRow}>
          <Button variant="outline" className={styles.railToggle} onClick={() => setRailOpen((v) => !v)} aria-expanded={railOpen} data-testid="rail-toggle">
            {codexTheme.castMenuToggle}
          </Button>
          <span className={styles.sectionLabel}>{codexTheme.personsHeading}</span>
          <Tabs items={tabItems} activeKey="entity" onChange={(k) => navigateToTab(k, route)} />
          <Button variant="outline" className={styles.panelToggle} onClick={() => setPanelOpen((v) => !v)} aria-expanded={panelOpen} data-testid="panel-toggle">
            {codexTheme.showStemmaToggle}
          </Button>
        </div>

        {failedWithNothing ? (
          <StateCard
            testId="state-error"
            label={codexTheme.stateError.label}
            headline={codexTheme.stateError.headline}
            body={codexTheme.stateError.body}
            actions={
              m.banner && (
                <Button variant="outline" onClick={() => m.requestChapter(m.banner?.failed ?? m.bookmark)} data-testid="state-retry">
                  {codexTheme.tryAgain}
                </Button>
              )
            }
          />
        ) : !vm ? (
          <Skeleton />
        ) : entity ? (
          <EntityMain vm={vm} entity={entity} onOpen={open} />
        ) : entityId === PENDING_ENTITY ? (
          <Skeleton />
        ) : (
          // Entity not present at this chapter (§6.7): neutral copy, never the old data,
          // never "appears later" (F4).
          <StateCard
            testId="state-not-present"
            label={codexTheme.stateNoMatch.label}
            headline={fillTemplate(codexTheme.stateNoMatch.headline, { n: roman(m.bookmark) })}
            body={codexTheme.stateNoMatch.body}
            actions={
              principal && (
                <Button variant="outline" onClick={() => open(principal.id)} data-testid="go-principal">
                  {codexTheme.goToPrincipal}
                </Button>
              )
            }
          />
        )}

        <div className={styles.spacer} />
        {vm && (
          <div className={styles.fenceLine} data-testid="fence-line">
            <span className={styles.fenceRule} />
            <span className={styles.fenceGlyph} title={codexTheme.fenceTooltip} data-testid="fence-glyph">
              <ArchDoorIcon size={16} />
            </span>
            <span className={styles.fenceCopy}>{fillTemplate(codexTheme.fence, { n: roman(m.bookmark) })}</span>
            <span className={styles.fenceRule} />
          </div>
        )}
      </main>

      <div
        className={`${styles.panelScrim} ${panelOpen || railOpen ? styles.panelOpen : ""}`}
        onMouseDown={() => { setPanelOpen(false); setRailOpen(false); }}
        data-testid="panel-scrim"
      />
      <aside className={`${styles.rightPanel} ${panelOpen ? styles.panelOpen : ""}`} data-testid="dossier-right-panel">
        {vm && entity && (
          <>
            <div className={styles.panelHeader}>
              <span className={styles.panelTitle}>{fillTemplate(codexTheme.stemmaOf, { name: entity.label })}</span>
              <a className={styles.panelLink} href={routePath({ name: "work-web", slug: route.slug, focus: entity.id })} data-testid="open-full">
                {codexTheme.openFull}
              </a>
            </div>
            <EgoGraph vm={vm} focusId={entity.id} onOpen={open} className={styles.ego} />
            <p className={styles.legend}>{codexTheme.legend}</p>
          </>
        )}
      </aside>
    </div>
  );
}

// Loading skeleton (§6.2 states): an H1 bar and three list bars, no spinner.
function Skeleton(): JSX.Element {
  return (
    <div className={styles.skeleton} data-testid="skeleton" aria-busy="true" aria-label={codexTheme.loading}>
      <div className={styles.skelH1} />
      <div className={styles.skelBar} />
      <div className={styles.skelBar} />
      <div className={styles.skelBar} />
    </div>
  );
}
