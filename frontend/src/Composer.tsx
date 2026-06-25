import { useEffect, useRef, useState } from "react";
import { appendChapters, fetchStatus, ingestWork, previewChapters } from "./api";
import type { AnalysisState, PreviewResponse, WorkModel } from "./types";

// The in-app ingest composer, in two modes:
//   create — a new novel (title + full text)
//   append — more chapters onto an existing novel (idempotent; rebuilds the graph)
// Either way the server splits the text into chapters by "Chapter N" headings; a live
// preview shows how many will land BEFORE committing, then we poll the rebuild to ready.

const PHASE_LABEL: Record<AnalysisState, string> = {
  queued: "Queued",
  extracting: "Finding the entities…",
  relating: "Drawing the connections…",
  ready: "Ready",
  error: "Couldn’t finish",
  unknown: "Working…",
};

const ACTIVE = new Set<AnalysisState>(["queued", "extracting", "relating", "unknown"]);

type Mode = "create" | "append";

export default function Composer({
  mode,
  work,
  onReady,
  onClose,
}: {
  mode: Mode;
  work?: WorkModel;
  onReady: (slug: string) => void;
  onClose: () => void;
}): JSX.Element {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [slug, setSlug] = useState<string | null>(null);
  const [state, setState] = useState<AnalysisState>("unknown");
  const [detail, setDetail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const timer = useRef<number | null>(null);

  // Live chapter-detection preview (debounced) — the SAME splitter the ingest uses, so
  // the count is trustworthy before commit. In append mode it also flags new vs present.
  useEffect(() => {
    const body = text.trim();
    if (!body) {
      setPreview(null);
      return;
    }
    let live = true;
    const id = window.setTimeout(() => {
      previewChapters(body, mode === "append" ? work?.slug : undefined)
        .then((p) => live && setPreview(p))
        .catch(() => live && setPreview(null));
    }, 350);
    return () => {
      live = false;
      window.clearTimeout(id);
    };
  }, [text, mode, work?.slug]);

  // Poll the analysis status once a commit has launched, until it settles.
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

  const detected = preview?.total ?? 0;
  const newCount = preview?.new_count ?? 0;
  const newChapters = (preview?.chapters ?? []).filter((c) => c.is_new);

  const canSubmit =
    !submitting &&
    !slug &&
    text.trim().length > 0 &&
    (mode === "append" ? newCount > 0 : title.trim().length > 0 && detected > 0);

  const submit = async (): Promise<void> => {
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "append" && work) {
        const resp = await appendChapters(work.slug, text);
        setSlug(resp.slug);
        setState((resp.state as AnalysisState) ?? "queued");
      } else {
        const resp = await ingestWork(title.trim(), text);
        setSlug(resp.slug);
        setState((resp.state as AnalysisState) ?? "queued");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const working = slug !== null;
  const heading = mode === "append" ? `Add chapters to ${work?.title ?? ""}` : "Add a novel";
  const dialogLabel = mode === "append" ? "Add chapters" : "Add a novel";

  return (
    <div className="composer-scrim" role="dialog" aria-modal="true" aria-label={dialogLabel}>
      <div className="composer">
        <button className="composer-x" onClick={onClose} aria-label="Close">
          ×
        </button>

        {!working ? (
          <>
            <h2 className="composer-title">{heading}</h2>
            <p className="composer-sub">
              Paste the full text — chapters are detected automatically from “Chapter N”
              headings.{" "}
              {mode === "append"
                ? "Chapters already in the novel are skipped; only new ones are added."
                : "Each link is tied to the chapter that reveals it."}
            </p>

            {mode === "create" ? (
              <label className="composer-field">
                <span className="composer-label">Title</span>
                <input
                  className="composer-input"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Title of the work"
                  autoFocus
                />
              </label>
            ) : null}

            <label className="composer-field">
              <span className="composer-label">Text</span>
              <textarea
                className="composer-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste the full text here…"
                rows={12}
                spellCheck={false}
                autoFocus={mode === "append"}
              />
            </label>

            {preview ? (
              <div className="detect-readout">
                {mode === "append" ? (
                  <>
                    <span className="detect-count">{newCount}</span> new{" "}
                    {newCount === 1 ? "chapter" : "chapters"} detected
                    {detected > newCount ? (
                      <span className="detect-dim"> · {detected - newCount} already added</span>
                    ) : null}
                    {newChapters.length > 0 ? (
                      <span className="detect-list">
                        {newChapters.map((c) => `ch ${c.ordinal}`).join(", ")}
                      </span>
                    ) : null}
                  </>
                ) : (
                  <>
                    <span className="detect-count">{detected}</span>{" "}
                    {detected === 1 ? "chapter" : "chapters"} detected
                  </>
                )}
              </div>
            ) : null}

            {error ? <div className="composer-error">{error}</div> : null}
            <div className="composer-actions">
              <button className="composer-cancel" onClick={onClose}>
                Cancel
              </button>
              <button className="enter composer-go" onClick={() => void submit()} disabled={!canSubmit}>
                {submitting
                  ? "Working…"
                  : mode === "append"
                    ? `Add ${newCount > 0 ? newCount : ""} ${newCount === 1 ? "chapter" : "chapters"}`.trim()
                    : "Begin analysis"}
              </button>
            </div>
          </>
        ) : (
          <div className="composer-progress">
            <h2 className="composer-title">{work?.title ?? title}</h2>
            <div className={`progress-state ${state}`}>
              {ACTIVE.has(state) ? <span className="spinner" aria-hidden /> : null}
              <span>
                {mode === "append" && ACTIVE.has(state) ? "Rebuilding the map… " : ""}
                {PHASE_LABEL[state]}
              </span>
            </div>
            {detail ? <div className="progress-detail">{detail}</div> : null}
            {state === "ready" ? (
              <button className="enter composer-go" onClick={() => onReady(slug)}>
                {mode === "append" ? "View updated map" : "Open the map"}
              </button>
            ) : null}
            {state === "error" ? (
              <>
                <p className="composer-sub">
                  The chapters are saved, but the analysis step needs the ML environment.
                  Run it from the CLI (<code>storyweave extract {slug}</code>) and reopen.
                </p>
                <button className="composer-cancel" onClick={() => onReady(slug)}>
                  {mode === "append" ? "Back to the map" : "Back to shelf"}
                </button>
              </>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
