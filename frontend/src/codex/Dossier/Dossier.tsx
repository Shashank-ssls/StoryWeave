import type { WorkRoute } from "../../router/useHashRoute";
import { useWorkTitle } from "../useWorkTitle";
import Tabs from "../../components/Tabs/Tabs";
import { codexTheme } from "../theme";
import { tabItems, navigateToTab } from "../tabs";
import styles from "./Dossier.module.css";

// DESIGN_SPEC.md §6.2 Dossier geometry. Rail/main/right-panel real dimensions; content is
// a placeholder box per column (R4 builds the real cast list, identity blocks, ties, etc).
export default function Dossier({ route }: { route: WorkRoute }): JSX.Element {
  const title = useWorkTitle(route.slug);

  return (
    <div className={styles.dossier} data-testid="dossier-root">
      <aside className={styles.rail} data-testid="dossier-rail">
        <div className={styles.wordmark}>StoryWeave</div>
        <div className={styles.novelTitle}>{title}</div>
        <div className={styles.placeholder}>chapter list + cast — R3/R4</div>
      </aside>

      <main className={styles.main}>
        <div className={styles.topRow}>
          <span className={styles.sectionLabel}>{codexTheme.personsHeading}</span>
          <Tabs items={tabItems} activeKey="entity" onChange={(k) => navigateToTab(k, route)} />
        </div>
        <div className={styles.placeholder}>H1 + lede + identity blocks + ties — R4</div>
      </main>

      <aside className={styles.rightPanel} data-testid="dossier-right-panel">
        <div className={styles.placeholder}>Ego graph — R4</div>
      </aside>
    </div>
  );
}
