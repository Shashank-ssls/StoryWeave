import styles from "./LoadingDots.module.css";

// DESIGN_SPEC.md §6.7 Loading state: "a 3-dot line glyph (ink -> dim -> faint; the dots
// fade in sequence, 1.2s loop; static under reduced motion)". Purely decorative — the
// StateCard's own role="status" + label already announce "Loading" to assistive tech.
export default function LoadingDots(): JSX.Element {
  return (
    <span className={styles.dots} aria-hidden="true" data-testid="loading-dots">
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className={styles.dot} />
    </span>
  );
}
