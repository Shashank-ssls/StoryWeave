import type { WorkRoute } from "../../router/useHashRoute";
import { useWorkTitle } from "../useWorkTitle";
import Tabs from "../../components/Tabs/Tabs";
import { tabItems, navigateToTab } from "../tabs";
import ChapterListCompact from "../chapter/ChapterListCompact";
import styles from "./Stemma.module.css";

// DESIGN_SPEC.md §6.3 The Stemma geometry. Canvas gets the centre mask (§4.6 rule 3) so
// no mural line is ever mistaken for a graph edge; the actual graph is R5.
export default function Stemma({ route }: { route: WorkRoute }): JSX.Element {
  const title = useWorkTitle();

  return (
    <div className={styles.stemma} data-testid="stemma-root">
      <aside className={styles.rail} data-testid="stemma-rail">
        <div className={styles.wordmark}>StoryWeave</div>
        <div className={styles.novelTitle}>{title}</div>
        <ChapterListCompact />
        <div className={styles.placeholder}>search + filters + cast size — R5</div>
      </aside>

      <div className={`${styles.canvas} web-canvas-mask`} data-testid="stemma-canvas">
        <div className={styles.canvasTopBar}>
          <span className={styles.focusLabel}>Focused on — R5</span>
          <Tabs items={tabItems} activeKey="web" onChange={(k) => navigateToTab(k, route)} />
        </div>
        <div className={styles.placeholder}>Cytoscape graph — R5</div>
      </div>

      <aside className={styles.rightPanel} data-testid="stemma-right-panel">
        <div className={styles.placeholder}>Selection panel — R5</div>
      </aside>
    </div>
  );
}
