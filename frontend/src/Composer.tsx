import { useEffect, useRef, useState } from "react";
import { fetchStatus, ingestWork } from "./api";
import type { AnalysisState } from "./types";

// The in-app ingest composer. Paste a title + chapters; the server ingests them in-process
// (chapters exist immediately) and launches extract→relate in the background. We poll the
// status route until the graph is ready — or report honestly if the ML step can't run.

const PHASE_LABEL: Record<AnalysisState, string> = {
  queued: "Queued",
  extracting: "Finding the entities…",
  relating: "Drawing the connections…",
  ready: "Ready",
  error: "Couldn’t finish",
  unknown: "Working…",
};

const ACTIVE = new Set<AnalysisState>(["queued", "extracting", "relating", "unknown"]);

// Chapters separated by a blank line + "Chapter N" heading is what the splitter detects;
// give people a concrete shape to paste into rather than a blank wall.
const PLACEHOLDER = `Chapter 1
She crossed the bridge before the lamps were lit…

Chapter 2
The letter bore no name, only a heron pressed into the wax…`;

export default function Composer({
  onReady,
  onClose,
}: {
  onReady: (slug: string) => void;
  onClose: () => void;
}): JSX.Element {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [slug, setSlug] = useState<string | null>(null);
  const [state, setState] = useState<AnalysisState>("unknown");
  const [detail, setDetail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const timer = useRef<number | null>(null);

  // Poll the analysis status once an ingest has launched, until it settles.
  useEffect(() => {
    if (!slug || !ACTIVE.has(state)) return;
    let live = true;
    const tick = async (): Promise<void> => {
      try {
        const st = await fetchStatus(slug);
        if (!live) return;
        setState(st.state);
        setDetail(st.detail);
      } catch (e: unknown) {
        if (live) setError(String(e));
      }
    };
    timer.current = window.setInterval(tick, 1500);
    void tick();
    return () => {
      live = false;
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [slug, state]);

  const canSubmit = title.trim().length > 0 && text.trim().length > 0 && !submitting && !slug;

  const submit = async (): Promise<void> => {
    setError(null);
    setSubmitting(true);
    try {
      const resp = await ingestWork(title.trim(), text);
      setSlug(resp.slug);
      setState((resp.state as AnalysisState) ?? "queued");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const working = slug !== null;

  return (
    <div className="composer-scrim" role="dialog" aria-modal="true" aria-label="Add a novel">
      <div className="composer">
        <button className="composer-x" onClick={onClose} aria-label="Close">
          ×
        </button>

        {!working ? (
          <>
            <h2 className="composer-title">Add a novel</h2>
            <p className="composer-sub">
              Paste the text. StoryWeave splits it into chapters and builds a spoiler-aware
              map — every link tied to the chapter that reveals it.
            </p>
            <label className="composer-field">
              <span className="composer-label">Title</span>
              <input
                className="composer-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="The Hollow Crown"
                autoFocus
              />
            </label>
            <label className="composer-field">
              <span className="composer-label">Text</span>
              <textarea
                className="composer-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={PLACEHOLDER}
                rows={12}
                spellCheck={false}
              />
            </label>
            {error ? <div className="composer-error">{error}</div> : null}
            <div className="composer-actions">
              <button className="composer-cancel" onClick={onClose}>
                Cancel
              </button>
              <button className="enter composer-go" onClick={() => void submit()} disabled={!canSubmit}>
                {submitting ? "Ingesting…" : "Begin analysis"}
              </button>
            </div>
          </>
        ) : (
          <div className="composer-progress">
            <h2 className="composer-title">{title}</h2>
            <div className={`progress-state ${state}`}>
              {ACTIVE.has(state) ? <span className="spinner" aria-hidden /> : null}
              <span>{PHASE_LABEL[state]}</span>
            </div>
            {detail ? <div className="progress-detail">{detail}</div> : null}
            {state === "ready" ? (
              <button className="enter composer-go" onClick={() => onReady(slug)}>
                Open <span className="enter-work">{title}</span>
              </button>
            ) : null}
            {state === "error" ? (
              <>
                <p className="composer-sub">
                  The chapters are saved, but the analysis step needs the ML environment.
                  You can run it from the CLI (<code>storyweave extract {slug}</code>) and
                  reopen the shelf.
                </p>
                <button className="composer-cancel" onClick={onClose}>
                  Back to shelf
                </button>
              </>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
