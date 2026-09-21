import { codexTheme } from "../theme";
import styles from "./Landing.module.css";

// DESIGN_SPEC.md §6.1 Landing — geometry + real theme copy where it's genuinely
// available (kicker/H1 are novel-independent, so using the real strings here isn't "fake
// story data"); everything novel-specific (lede, try-it panel, shelf) is a placeholder —
// that's R8's scope.
export default function Landing(): JSX.Element {
  return (
    <div className={styles.landing} data-testid="landing-root">
      <header className={styles.header}>
        <div className={styles.wordmark}>StoryWeave</div>
        <nav className={styles.headerLinks}>
          <span>How the seal works</span>
          <span>Source</span>
        </nav>
      </header>

      <div className={styles.mainRow}>
        <div className={styles.leftColumn}>
          <p className={styles.kicker}>{codexTheme.landingKicker}</p>
          <h1 className={styles.h1}>{codexTheme.landingH1}</h1>
          <div className={styles.placeholder}>lede + trust line — R8</div>
        </div>
        <div className={styles.tryItPanel}>
          <div className={styles.placeholder}>Try the sample panel — R8</div>
        </div>
      </div>

      <footer className={styles.footer}>
        <span className={styles.shelfLabel}>Your shelf:</span>
        <div className={styles.placeholder}>shelf + Add a novel — R8</div>
      </footer>
    </div>
  );
}
