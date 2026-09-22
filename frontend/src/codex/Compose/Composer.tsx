import { useEffect, useRef, useState } from "react";
import { appendChapters, fetchStatus, ingestWork, previewChapters } from "../../api";
import type { AnalysisState, PreviewResponse, WorkModel } from "../../types";
import Button from "../../components/Button/Button";
import Input from "../../components/Input/Input";
import LoadingDots from "../states/LoadingDots";
import styles from "./Composer.module.css";

// The in-app ingest form, ported from the pre-redesign app (R9 step 8) into the Codex UI
// as a real route (`#/add`) rather than the old modal-over-the-shelf overlay. Same two
// modes as before — create — a new novel (title + full text); append — more chapters onto
// an existing novel (idempotent; rebuilds the graph) — and the same backend calls
// unchanged (R3: backend frozen during the redesign). The server splits text into
// chapters by "Chapter N" headings; a live preview shows how many will land BEFORE
// committing, then this polls the rebuild to ready.
//
// Only `mode="create"` has a reachable entry point in the redesign (DESIGN_SPEC §6.1's
// "Add a novel"); `mode="append"` has no new-UI trigger yet (the old per-work "add
// chapters" action lived in the retired Library screen, and nothing in DESIGN_SPEC
// specs a replacement) — kept fully working here, not deleted, since the backend still
// supports it and dropping it would be a silent feature loss nobody asked for.

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
  onCancel,
}: {
  mode: Mode;
  work?: WorkModel;
  onReady: (slug: string) => void;
  onCancel: () => void;
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

  return (
    <div className={styles.card}>
      {!working ? (
        <>
          <h1 className={styles.title}>{heading}</h1>
          <p className={styles.sub}>
            Paste the full text — chapters are detected automatically from "Chapter N"
            headings.{" "}
            {mode === "append"
              ? "Chapters already in the novel are skipped; only new ones are added."
              : "Each link is tied to the chapter that reveals it."}
          </p>

          {mode === "create" ? (
            <label className={styles.field}>
              <span className={styles.label}>Title</span>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Title of the work"
                autoFocus
                data-testid="compose-title"
              />
            </label>
          ) : null}

          <label className={styles.field}>
            <span className={styles.label}>Text</span>
            <textarea
              className={styles.textarea}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the full text here…"
              rows={12}
              spellCheck={false}
              autoFocus={mode === "append"}
              data-testid="compose-text"
            />
          </label>

          {preview ? (
            <div className={styles.readout} data-testid="compose-readout">
              {mode === "append" ? (
                <>
                  <span className={styles.readoutCount}>{newCount}</span> new{" "}
                  {newCount === 1 ? "chapter" : "chapters"} detected
                  {detected > newCount ? (
                    <span className={styles.readoutDim}> · {detected - newCount} already added</span>
                  ) : null}
                  {newChapters.length > 0 ? (
                    <span className={styles.readoutDim}>
                      {" "}
                      ({newChapters.map((c) => `ch ${c.ordinal}`).join(", ")})
                    </span>
                  ) : null}
                </>
              ) : (
                <>
                  <span className={styles.readoutCount}>{detected}</span>{" "}
                  {detected === 1 ? "chapter" : "chapters"} detected
                </>
              )}
            </div>
          ) : null}

          {error ? (
            <div className={styles.error} role="alert" data-testid="compose-error">
              {error}
            </div>
          ) : null}

          <div className={styles.actions}>
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={!canSubmit} data-testid="compose-submit">
              {submitting
                ? "Working…"
                : mode === "append"
                  ? `Add ${newCount > 0 ? newCount : ""} ${newCount === 1 ? "chapter" : "chapters"}`.trim()
                  : "Begin analysis"}
            </Button>
          </div>
        </>
      ) : (
        <div className={styles.progress} data-testid="compose-progress">
          <h1 className={styles.title}>{work?.title ?? title}</h1>
          <div className={styles.progressState}>
            {ACTIVE.has(state) ? <LoadingDots /> : null}
            <span>
              {mode === "append" && ACTIVE.has(state) ? "Rebuilding the map… " : ""}
              {PHASE_LABEL[state]}
            </span>
          </div>
          {detail ? <div className={styles.progressDetail}>{detail}</div> : null}
          {state === "ready" ? (
            <Button onClick={() => onReady(slug)} data-testid="compose-open">
              {mode === "append" ? "View updated map" : "Open the map"}
            </Button>
          ) : null}
          {state === "error" ? (
            <>
              <p className={styles.sub}>
                The chapters are saved, but the analysis step needs the ML environment. Run
                it from the CLI (<code>storyweave extract {slug}</code>) and reopen.
              </p>
              <Button variant="outline" onClick={() => onReady(slug)}>
                {mode === "append" ? "Back to the map" : "Back to shelf"}
              </Button>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
