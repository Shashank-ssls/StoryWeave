import type { WorkRoute } from "../../router/useHashRoute";
import { useWorkTitle } from "../useWorkTitle";
import Tabs from "../../components/Tabs/Tabs";
import { tabItems, navigateToTab } from "../tabs";
import styles from "./Chronicle.module.css";

// DESIGN_SPEC.md §6.4 Chronicle geometry. Unlike Dossier/Stemma, there is no left rail —
// a horizontal 76px header bar instead, carrying the tabs.
export default function Chronicle({ route }: { route: WorkRoute }): JSX.Element {
  const title = useWorkTitle();

  return (
    <div className={styles.chronicle} data-testid="chronicle-root">
      <header className={styles.headerBar} data-testid="chronicle-header">
        <div className={styles.titleBlock}>
          <div className={styles.novelTitle}>{title}</div>
          <div className={styles.subtitle}>the chronicle, as far as you have read</div>
        </div>
        <Tabs items={tabItems} activeKey="chronicle" onChange={(k) => navigateToTab(k, route)} />
      </header>

      <div className={styles.body}>
        <div className={styles.chart}>
          <div className={styles.placeholder}>Chart (rows/columns/threads) — R7</div>
        </div>
        <aside className={styles.rightPanel} data-testid="chronicle-right-panel">
          <div className={styles.placeholder}>Selected reveal panel — R7</div>
        </aside>
      </div>
    </div>
  );
}
