import type { CodexRoute } from "../router/useHashRoute";
import Landing from "./Landing/Landing";
import Compose from "./Compose/Compose";
import Dossier from "./Dossier/Dossier";
import Stemma from "./Stemma/Stemma";
import { ChapterProvider, DEFAULT_VIEW, FULL_VIEW } from "./chapter/ChapterProvider";
import ChapterChrome from "./chapter/ChapterChrome";
import RevealChrome from "./reveal/RevealChrome";
import { useGlobalShortcuts } from "./shortcuts/useGlobalShortcuts";
import ShortcutSheet from "./shortcuts/ShortcutSheet";
import styles from "./CodexApp.module.css";

// The Codex UI's root: mural + vignette fixed background layers (DESIGN_SPEC.md §4.6
// rules 1-2), mounted once here so every new screen sits on them, then routes to the
// screen for the current URL. `.mural`/`.vignette` are tokens.css's own GLOBAL classes
// (not CSS-modules-scoped) — they're the foundation everything else sits on, so they stay
// as tokens.css defines them rather than being re-declared here.
//
// Inside a work, one ChapterProvider (keyed by slug) wraps all three tabs: the bookmark,
// payload cache and in-flight request are shared across the Dossier and the Stemma and
// survive tab switches, and are torn down whole when the slug changes (R3).
export default function CodexApp({ route }: { route: CodexRoute }): JSX.Element {
  // R9 §8.5: one global keyboard map for the whole app root — `g d`/`g w`/`g c` (only
  // meaningful inside a work; the hook itself checks the route) and `?`'s shortcut sheet.
  const { sheetOpen, closeSheet } = useGlobalShortcuts(route);
  return (
    <div className={styles.root}>
      <div className="mural" aria-hidden="true" />
      <div className="vignette" aria-hidden="true" />
      <div className={styles.content}>
        {route.name === "landing" ? (
          <Landing />
        ) : route.name === "add" ? (
          <Compose />
        ) : (
          <ChapterProvider
            key={route.slug}
            slug={route.slug}
            // R7: the route decides what the FIRST payload should be, so a first visit
            // costs exactly one /graph request. The Dossier needs the whole fenced graph
            // (it is reached by entity URL and must never say "not present" about someone
            // the reader has met); the Stemma opens on rule 2's default view.
            initialView={route.name === "work-entity" ? FULL_VIEW : DEFAULT_VIEW}
          >
            <RevealChrome>
              {route.name === "work-entity" && <Dossier route={route} />}
              {route.name === "work-web" && <Stemma route={route} />}
              <ChapterChrome />
            </RevealChrome>
          </ChapterProvider>
        )}
      </div>
      {sheetOpen && <ShortcutSheet onClose={closeSheet} />}
    </div>
  );
}
