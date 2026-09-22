import { navigate } from "../../router/useHashRoute";
import { PENDING_ENTITY } from "../../router/useHashRoute";
import Composer from "./Composer";
import styles from "./Compose.module.css";

// `#/add` (R9 step 8): the ported ingest form, now a real route on the mural/vignette
// background every other Codex screen sits on (mounted by CodexApp), rather than a modal
// bolted over the old shelf. Only `mode="create"` has a caller — see Composer.tsx's own
// header comment for why `append` stays in the component but unwired here.
export default function Compose(): JSX.Element {
  const goToWork = (slug: string): void => navigate({ name: "work-entity", slug, entityId: PENDING_ENTITY });
  const cancel = (): void => navigate({ name: "landing" });

  return (
    <div className={styles.compose} data-testid="compose-root">
      <header className={styles.header}>
        <button type="button" className={styles.wordmark} onClick={cancel}>
          StoryWeave
        </button>
      </header>
      <div className={styles.body}>
        <Composer mode="create" onReady={goToWork} onCancel={cancel} />
      </div>
    </div>
  );
}
