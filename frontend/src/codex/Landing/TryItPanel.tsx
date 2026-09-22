import { useMemo } from "react";
import { navigate, PENDING_ENTITY } from "../../router/useHashRoute";
import Button from "../../components/Button/Button";
import { EyeIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "../chapter/roman";
import { DEMO_SLUG } from "../../ontology";
import { ChapterProvider, useChapter } from "../chapter/ChapterProvider";
import ChapterChrome from "../chapter/ChapterChrome";
import RevealChrome from "../reveal/RevealChrome";
import StateCard from "../states/StateCard";
import { buildViewModel } from "../../graph/viewModel";
import ChapterStepper from "./ChapterStepper";
import MiniGraph from "./MiniGraph";
import styles from "./Landing.module.css";

// DESIGN_SPEC.md §6.1 "Try the sample" panel. Wrapped in its OWN ChapterProvider (keyed
// to the demo slug) so the stepper reads and writes the SAME per-work bookmark
// (`storyweave:bookmark:the-hollow-crown`) through the SAME fetch/cache/reveal machinery
// as the Dossier/Stemma/Chronicle — not a second implementation of any of it. Stepping
// forward therefore plays the real R6 reveal overlay unchanged when it crosses one.
function TryItInner(): JSX.Element {
  const m = useChapter();
  const vm = useMemo(() => (m.data ? buildViewModel(m.data) : null), [m.data]);

  if (m.workError) {
    return <StateCard testId="state-demo-missing" label={codexTheme.stateDemoMissing.label} headline={codexTheme.stateDemoMissing.headline} body={codexTheme.stateDemoMissing.body} />;
  }
  if (!m.work || !vm) {
    return (
      <StateCard
        testId="try-it-loading"
        label={codexTheme.stateLoading.label}
        headline={codexTheme.stateLoading.headline}
        body={fillTemplate(codexTheme.stateLoading.body, { n: roman(m.loading ?? m.bookmark) })}
        loading
      />
    );
  }

  const openDossier = (): void => navigate({ name: "work-entity", slug: DEMO_SLUG, entityId: PENDING_ENTITY });

  return (
    <div className={styles.tryIt}>
      <div className={styles.tryItTitleRow}>
        <span className={styles.tryItTitle}>{m.work.title}</span>
        <span className={styles.tryItMeta}>{fillTemplate(codexTheme.sampleMeta, { n: m.work.chapter_count })}</span>
      </div>

      <ChapterStepper bookmark={m.bookmark} chapterCount={m.work.chapter_count} onStep={(n) => m.requestChapter(n)} />

      <MiniGraph vm={vm} className={styles.miniGraph} />

      <div className={styles.promptRow} data-testid="landing-prompt">
        <EyeIcon size={24} className={styles.promptEye} />
        <span className={styles.promptText}>{codexTheme.landingPrompt}</span>
      </div>

      {m.bookmark > 1 && (
        <Button variant="outline" className={styles.exploreButton} onClick={openDossier} data-testid="explore-full-book">
          {codexTheme.exploreFullBook}
        </Button>
      )}

      <ChapterChrome />
    </div>
  );
}

export default function TryItPanel(): JSX.Element {
  return (
    <ChapterProvider slug={DEMO_SLUG}>
      <RevealChrome>
        <TryItInner />
      </RevealChrome>
    </ChapterProvider>
  );
}
