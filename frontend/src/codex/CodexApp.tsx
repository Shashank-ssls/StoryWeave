import type { CodexRoute } from "../router/useHashRoute";
import Landing from "./Landing/Landing";
import Dossier from "./Dossier/Dossier";
import Stemma from "./Stemma/Stemma";
import Chronicle from "./Chronicle/Chronicle";
import styles from "./CodexApp.module.css";

// The Codex UI's root: mural + vignette fixed background layers (DESIGN_SPEC.md §4.6
// rules 1-2), mounted once here so every new screen sits on them, then routes to the
// screen for the current URL. `.mural`/`.vignette` are tokens.css's own GLOBAL classes
// (not CSS-modules-scoped) — they're the foundation everything else sits on, so they stay
// as tokens.css defines them rather than being re-declared here.
export default function CodexApp({ route }: { route: CodexRoute }): JSX.Element {
  return (
    <div className={styles.root}>
      <div className="mural" aria-hidden="true" />
      <div className="vignette" aria-hidden="true" />
      <div className={styles.content}>
        {route.name === "landing" && <Landing />}
        {route.name === "work-entity" && <Dossier route={route} />}
        {route.name === "work-web" && <Stemma route={route} />}
        {route.name === "work-chronicle" && <Chronicle route={route} />}
      </div>
    </div>
  );
}
