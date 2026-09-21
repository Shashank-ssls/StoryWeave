import type { ReactNode } from "react";
import styles from "./StateCard.module.css";

// The §6.7 state card language, shared by every state: UI 13 --dim label, Display 36-40
// headline, italic Body 20 --dim explanation, optional actions. Copy comes from the
// theme (codexTheme.state*); this component only lays it out.
export default function StateCard({
  label,
  headline,
  body,
  actions,
  testId,
}: {
  label: string;
  headline: string;
  body: string;
  actions?: ReactNode;
  testId?: string;
}): JSX.Element {
  return (
    <section className={styles.card} data-testid={testId} role="status">
      <div className={styles.label}>{label}</div>
      <h2 className={styles.headline}>{headline}</h2>
      <p className={styles.body}>{body}</p>
      {actions && <div className={styles.actions}>{actions}</div>}
    </section>
  );
}
