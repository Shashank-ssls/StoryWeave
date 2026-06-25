import { useCallback, useEffect, useMemo, useState } from "react";
import { deleteWork, fetchGraph, fetchWorks } from "./api";
import type { GraphElements, WorkModel } from "./types";
import { DEMO_SLUG, NODE_TYPES, TYPE_COLOR, relationLabel } from "./ontology";
import GraphView, { type Selection } from "./GraphView";
import Library from "./Library";
import Composer from "./Composer";

const EMPTY: GraphElements = { nodes: [], edges: [] };

function Legend(): JSX.Element {
  return (
    <div className="legend" aria-label="Entity types">
      <div className="legend-title">Entities</div>
      <div className="legend-grid">
        {NODE_TYPES.map((t) => (
          <span className="legend-item" key={t}>
            <span className="swatch" style={{ background: TYPE_COLOR[t] }} />
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

function DetailPanel({ sel }: { sel: Selection }): JSX.Element | null {
  if (!sel) return null;
  if (sel.kind === "node") {
    const d = sel.data;
    const props = Object.entries(d.properties);
    return (
      <aside className="detail" role="complementary">
        <div className="detail-kind" style={{ color: TYPE_COLOR[d.type as keyof typeof TYPE_COLOR] }}>
          {d.subtype ? `${d.type} · ${d.subtype}` : d.type}
        </div>
        <h2>{d.label}</h2>
        <dl>
          <dt>Revealed</dt>
          <dd>chapter {d.revealed_chapter}</dd>
          {d.evidence_span && (
            <>
              <dt>Evidence</dt>
              <dd className="quote">“{d.evidence_span}”</dd>
            </>
          )}
          {props.length > 0 && (
            <>
              <dt>Known</dt>
              <dd>
                {props.map(([k, v]) => (
                  <div key={k}>
                    <span className="pk">{k}</span> {v}
                  </div>
                ))}
              </dd>
            </>
          )}
        </dl>
        <div className="prov">via {d.extraction_method}</div>
      </aside>
    );
  }
  const d = sel.data;
  const kind = d.tier === 3 ? "identity reveal" : d.tier === 2 ? "social link" : "structural link";
  return (
    <aside className="detail" role="complementary">
      <div className="detail-kind" style={d.tier === 3 ? { color: "var(--reveal)" } : undefined}>
        {kind}
      </div>
      <h2 className="rel">{relationLabel(d.relation)}</h2>
      <dl>
        <dt>Revealed</dt>
        <dd>chapter {d.revealed_chapter}</dd>
        {d.evidence_span && (
          <>
            <dt>Evidence</dt>
            <dd className="quote">“{d.evidence_span}”</dd>
          </>
        )}
      </dl>
      <div className="prov">via {d.extraction_method}</div>
    </aside>
  );
}

// Destructive action → a confirmation that NAMES the work (CLAUDE.md: ask before
// destructive actions). The delete is a true delete of local data; the demo can't
// reach here (it has no delete control).
function ConfirmDelete({
  work,
  busy,
  onConfirm,
  onCancel,
}: {
  work: WorkModel;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}): JSX.Element {
  return (
    <div className="composer-scrim" role="dialog" aria-modal="true" aria-label="Confirm delete">
      <div className="confirm">
        <h2 className="confirm-title">Delete this novel?</h2>
        <p className="confirm-body">
          Delete <span className="confirm-work">{work.title}</span> and its map? This
          removes its local data and can’t be undone.
        </p>
        <div className="composer-actions">
          <button className="composer-cancel" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="confirm-go" onClick={onConfirm} disabled={busy}>
            {busy ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function App(): JSX.Element {
  const [works, setWorks] = useState<WorkModel[]>([]);
  const [work, setWork] = useState<WorkModel | null>(null);
  const [composing, setComposing] = useState(false);
  const [appending, setAppending] = useState(false);
  const [n, setN] = useState(1);
  const [elements, setElements] = useState<GraphElements>(EMPTY);
  const [sel, setSel] = useState<Selection>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<WorkModel | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadWorks = useCallback(
    () =>
      fetchWorks()
        .then((w) => {
          setWorks(w);
          return w;
        })
        .catch((e: unknown) => {
          setError(String(e));
          return [] as WorkModel[];
        }),
    [],
  );

  useEffect(() => {
    void loadWorks();
  }, [loadWorks]);

  // Every slider move RE-QUERIES the server at N. The fence is server-side, so the
  // payload itself only holds revealed-at-N data — the client never post-filters.
  useEffect(() => {
    if (!work) return;
    let live = true;
    fetchGraph(work.slug, n)
      .then((g) => live && setElements(g.elements))
      .catch((e: unknown) => setError(String(e)));
    return () => {
      live = false;
    };
  }, [work, n]);

  const enter = useCallback((w: WorkModel) => {
    setWork(w);
    setN(1);
    setElements(EMPTY);
    setSel(null);
    setAppending(false);
    setError(null);
  }, []);

  // After an append, the work has more chapters: extend the slider to the new max and
  // jump to the end so the just-added chapters' reveals are visible. The graph re-queries
  // off the new `work`/`n` (the rebuild already ran before the modal said ready).
  const onAppended = useCallback(
    async (slug: string) => {
      setAppending(false);
      const fresh = await loadWorks();
      const updated = fresh.find((w) => w.slug === slug);
      if (updated) {
        setWork(updated);
        setN(updated.chapter_count);
        setSel(null);
      }
    },
    [loadWorks],
  );

  const toLibrary = useCallback(() => {
    setWork(null);
    void loadWorks();
  }, [loadWorks]);

  const onComposed = useCallback(
    async (slug: string) => {
      setComposing(false);
      const fresh = await loadWorks();
      const target = fresh.find((w) => w.slug === slug);
      if (target) enter(target);
    },
    [loadWorks, enter],
  );

  const confirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteWork(pendingDelete.slug);
      setPendingDelete(null);
      await loadWorks();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeleting(false);
    }
  }, [pendingDelete, loadWorks]);

  const onSelect = useCallback((s: Selection) => setSel(s), []);
  const max = work?.chapter_count ?? 1;
  const counts = useMemo(
    () => ({ nodes: elements.nodes.length, edges: elements.edges.length }),
    [elements],
  );

  if (!work) {
    return (
      <>
        <Library
          works={works}
          onEnter={enter}
          onAdd={() => setComposing(true)}
          onDelete={setPendingDelete}
        />
        {composing ? (
          <Composer
            mode="create"
            onReady={(slug) => void onComposed(slug)}
            onClose={() => setComposing(false)}
          />
        ) : null}
        {pendingDelete ? (
          <ConfirmDelete
            work={pendingDelete}
            busy={deleting}
            onConfirm={() => void confirmDelete()}
            onCancel={() => setPendingDelete(null)}
          />
        ) : null}
      </>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <button className="home-link" onClick={toLibrary} aria-label="Back to the library">
            <span className="back-chevron" aria-hidden>
              ‹
            </span>
            <span className="star">✦</span>
            <span className="mark">StoryWeave</span>
          </button>
          <span className="work">{work.title}</span>
        </div>
        <div className="topbar-right">
          {work.slug !== DEMO_SLUG ? (
            <button className="add-chapters" onClick={() => setAppending(true)}>
              + Add chapters
            </button>
          ) : null}
          <div className="readout">
            <span>ch {n}</span>
            <span>{counts.nodes} entities</span>
            <span>{counts.edges} links</span>
          </div>
        </div>
      </header>

      <main className="stage">
        {error ? (
          <div className="error">
            <div>{error}</div>
            <div className="hint">Is the API running? `uvicorn storyweave.api.app:app`</div>
          </div>
        ) : (
          <GraphView elements={elements} onSelect={onSelect} />
        )}
        <Legend />
        <DetailPanel sel={sel} />
        {appending ? (
          <Composer
            mode="append"
            work={work}
            onReady={(slug) => void onAppended(slug)}
            onClose={() => setAppending(false)}
          />
        ) : null}
      </main>

      <footer className="reading">
        <span className="reading-label">Reading position</span>
        <input
          className="scrubber"
          type="range"
          min={1}
          max={max}
          step={1}
          value={n}
          aria-label="Chapter"
          onChange={(e) => setN(Number(e.target.value))}
        />
        <span className="reading-num">
          chapter <b>{n}</b> <span className="of">of {max}</span>
        </span>
      </footer>
    </div>
  );
}
