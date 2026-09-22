import { useEffect, useState } from "react";
import { navigate, routePath } from "../../router/useHashRoute";
import { fetchWorks } from "../../api";
import type { WorkModel } from "../../types";
import { DEMO_SLUG } from "../../ontology";
import { codexTheme } from "../theme";
import StateCard from "../states/StateCard";
import Button from "../../components/Button/Button";
import ExplainerPanel from "./ExplainerPanel";
import TryItPanel from "./TryItPanel";
import styles from "./Landing.module.css";

const REPO_URL = "https://github.com/Shashank-ssls/StoryWeave";

type WorksState = { status: "loading" } | { status: "ready"; works: WorkModel[] } | { status: "error" };

function useWorks(): WorksState {
  const [state, setState] = useState<WorksState>({ status: "loading" });
  useEffect(() => {
    let live = true;
    fetchWorks()
      .then((works) => live && setState({ status: "ready", works }))
      .catch(() => live && setState({ status: "error" }));
    return () => {
      live = false;
    };
  }, []);
  return state;
}

// DESIGN_SPEC.md §6.1 Landing. The try-it panel (its own ChapterProvider, keyed to the
// demo) is the only part of this screen that touches story data — everything else here
// (kicker/H1/lede/trust line/shelf) is novel-independent copy or the plain /works list.
export default function Landing(): JSX.Element {
  const [explainerOpen, setExplainerOpen] = useState(false);
  const worksState = useWorks();

  return (
    <div className={styles.landing} data-testid="landing-root">
      <header className={styles.header}>
        <div className={styles.wordmark}>StoryWeave</div>
        <nav className={styles.headerLinks}>
          <button type="button" className={styles.headerLink} onClick={() => setExplainerOpen(true)} data-testid="how-seal-works">
            {codexTheme.howSealWorks}
          </button>
          <a className={styles.headerLink} href={REPO_URL} target="_blank" rel="noreferrer">
            {codexTheme.sourceLink}
          </a>
        </nav>
      </header>

      <div className={styles.mainRow}>
        <div className={styles.leftColumn}>
          <p className={styles.kicker}>{codexTheme.landingKicker}</p>
          <h1 className={styles.h1}>{codexTheme.landingH1}</h1>
          <p className={styles.lede}>{codexTheme.landingLede}</p>
          <p className={styles.trustLine}>{codexTheme.landingTrust}</p>
        </div>
        <div className={styles.tryItPanel} data-testid="try-it-panel">
          {worksState.status === "loading" ? (
            <StateCard testId="try-it-loading" label={codexTheme.stateLoading.label} headline={codexTheme.stateLoading.headline} body="" loading />
          ) : worksState.status === "error" ? (
            <StateCard testId="state-try-it-error" label={codexTheme.stateError.label} headline={codexTheme.stateError.headline} body={codexTheme.stateError.body} />
          ) : worksState.works.some((w) => w.slug === DEMO_SLUG) ? (
            <TryItPanel />
          ) : (
            <StateCard testId="state-demo-missing" label={codexTheme.stateDemoMissing.label} headline={codexTheme.stateDemoMissing.headline} body={codexTheme.stateDemoMissing.body} />
          )}
        </div>
      </div>

      <footer className={styles.footer}>
        <span className={styles.shelfLabel}>{codexTheme.yourShelf}</span>
        {worksState.status === "loading" ? (
          <span className={styles.shelfLoading} data-testid="shelf-loading" />
        ) : worksState.status === "error" ? (
          <StateCard testId="state-shelf-error" label={codexTheme.stateError.label} headline={codexTheme.stateError.headline} body={codexTheme.stateError.body} />
        ) : worksState.works.length === 0 ? (
          <StateCard
            testId="state-empty-shelf"
            label={codexTheme.stateEmptyShelf.label}
            headline={codexTheme.stateEmptyShelf.headline}
            body={codexTheme.stateEmptyShelf.body}
            actions={
              <>
                <Button variant="outline" onClick={() => navigate({ name: "legacy" })} data-testid="open-sample">
                  {codexTheme.openSample}
                </Button>
                <Button variant="outline" onClick={() => navigate({ name: "legacy" })} data-testid="add-novel-empty">
                  {codexTheme.addNovel}
                </Button>
              </>
            }
          />
        ) : (
          <div className={styles.shelf} data-testid="landing-shelf">
            {worksState.works.map((w) => (
              <a key={w.slug} className={styles.shelfCard} href={routePath({ name: "work-entity", slug: w.slug, entityId: "_pending" })}>
                <span className={styles.shelfCardTitle}>{w.title}</span>
                <span className={styles.shelfCardMeta}>{w.chapter_count} {w.chapter_count === 1 ? "chapter" : "chapters"}</span>
              </a>
            ))}
            {/* R8: no dedicated ingestion screen exists in the redesign — the backend's
                real ingest endpoint (POST /api/v1/works) is already wired up behind the
                legacy Composer (#/_legacy), so "Add a novel" reuses that route as-is
                rather than building a second ingestion UI (out of scope, per the brief). */}
            <button type="button" className={styles.shelfAdd} onClick={() => navigate({ name: "legacy" })} data-testid="add-novel">
              <span className={styles.shelfAddPlus}>+</span>
              <span>{codexTheme.addNovel}</span>
              <span className={styles.shelfCardMeta}>{codexTheme.addNovelCaption}</span>
            </button>
          </div>
        )}
      </footer>

      {explainerOpen && <ExplainerPanel onClose={() => setExplainerOpen(false)} />}
    </div>
  );
}
