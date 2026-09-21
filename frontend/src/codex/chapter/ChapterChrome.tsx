import { useEffect } from "react";
import Button from "../../components/Button/Button";
import { CloseIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { roman } from "./roman";
import { useChapter } from "./ChapterProvider";
import ChapterDialog from "./ChapterDialog";
import styles from "./ChapterChrome.module.css";

// The per-work overlays that hang off the chapter model: the forward-loading wash
// (§8.1 step 1), the error banner (§6.7), the two toasts (§8.1), the dialog (§6.6) and the
// `[` / `]` keys (§8.5). Mounted once inside ChapterProvider by CodexApp so every in-work
// screen gets all of it without wiring anything itself.

function isTypingTarget(t: EventTarget | null): boolean {
  if (!(t instanceof HTMLElement)) return false;
  return t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable;
}

export default function ChapterChrome(): JSX.Element {
  const m = useChapter();

  // Keyboard: `[` steps back immediately (backward path — nothing can be exposed);
  // `]` never moves the bookmark itself, it only opens the dialog prefilled with the
  // next chapter so forward always goes through confirm. A window listener is the only
  // way to catch keys while nothing inside the app root has focus (focus sits on <body>
  // after a click), so the "scoped to the app root, never on inputs" rule (§8.5) is
  // enforced by the target check instead: typing targets and the open dialog are ignored.
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (m.dialog.open || isTypingTarget(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === "[") {
        e.preventDefault();
        m.requestChapter(m.bookmark - 1);
      } else if (e.key === "]") {
        e.preventDefault();
        m.openDialog(m.bookmark + 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [m]);

  const forwardLoading = m.loading !== null && m.data !== null;

  return (
    <>
      {forwardLoading && (
        <div className={styles.wash} data-testid="loading-wash" aria-hidden="true">
          <span className={styles.washText}>
            {codexTheme.loading} {fillTemplate(codexTheme.loadingUpTo, { n: roman(m.loading ?? 0) })}
          </span>
        </div>
      )}

      {/* The banner is for a failure with older data still on screen (§6.7). When
          nothing is on screen (initial load failed, or a backward move's fetch failed
          after its purge) the screen itself shows the §6.7 error CARD instead. */}
      {m.banner && m.banner.showing !== null && (
        <div className={styles.banner} role="alert" data-testid="error-banner">
          <span>
            {fillTemplate(codexTheme.bannerError, {
              failed: roman(m.banner.failed),
              showing: roman(m.banner.showing),
            })}
          </span>
          <Button variant="quiet" onClick={() => m.requestChapter(m.banner?.failed ?? m.bookmark)} data-testid="banner-retry">
            {codexTheme.tryAgain}
          </Button>
          <Button variant="icon" aria-label={codexTheme.close} onClick={m.dismissBanner}>
            <CloseIcon size={16} />
          </Button>
        </div>
      )}

      {m.toast && (
        <div className={styles.toast} role="status" aria-live="polite" data-testid="toast" data-kind={m.toast.kind}>
          {m.toast.kind === "backward"
            ? fillTemplate(codexTheme.toastBackward, { n: roman(m.toast.n) })
            : fillTemplate(
                // TODO(R6): when the diff has identity edges the reveal overlay (§8.2)
                // replaces this toast. Until then the same quiet toast is shown, marked.
                m.toast.diff.newIdentityEdges.length > 0 ? codexTheme.toastForwardIdentity : codexTheme.toastForward,
                {
                  n: roman(m.toast.n),
                  names: codexTheme.newNames(m.toast.diff.newNodes.length),
                  ties: codexTheme.newTies(m.toast.diff.newEdges.length),
                },
              )}
        </div>
      )}

      <ChapterDialog />
    </>
  );
}
