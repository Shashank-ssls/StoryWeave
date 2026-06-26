import { useCallback, useEffect, useMemo, useState } from "react";
import { deleteWork, fetchGraph, fetchWorks } from "./api";
import type { GraphElements, WorkModel } from "./types";
import { DEMO_SLUG, NODE_TYPES, TYPE_COLOR, relationLabel } from "./ontology";
import GraphView, { type Selection } from "./GraphView";
import Library from "./Library";
import Composer from "./Composer";

const EMPTY: GraphElements = { nodes: [], edges: [] };

// Default-on degree view (Part 1): open the graph showing only the connected core so a
// dense work (e.g. 84-node Shadow Slave ch3) opens legible instead of as a hairball.
// Chosen FROM THE DATA, not guessed: at that graph degree-0 nodes are true orphans
// (`governments`, `city`) and degree-1 nodes are single-mention background leaves
// (`rusty bench`, `national militaries`, the privileged-casts chain) — so hiding
// degree < 2 drops exactly that periphery (9 of 84) while keeping every node with ≥2
// links. PURE VIEW: nothing is deleted; dragging the filter to "all" (0) reveals every
// node, and the "X of Y" readout keeps it honest that nodes are hidden, not gone.
const DEFAULT_MIN_DEGREE = 2;

// Salience demotion (default-ON view layer): "background" nodes are generic common-noun
// pseudo-characters GLiNER over-promotes — `policeman`, `soldier`, `child`, `the younger
// soldier` — which are distinct/background people, NOT one salient character (proven by a
// coref measurement: they must NOT be merged). A real Character name is a proper noun and
// carries an uppercase letter; a generic common-noun reference is all-lowercase. So the
// signal is precise and needs no model: Character + no uppercase = background. This is a
// reversible VIEW judgement (a toggle), never a persisted salience verdict or a deletion —
// per the navigation principle that importance stays user-driven and every node reachable.
function isBackground(type: string, label: string): boolean {
  return type === "Character" && label === label.toLowerCase();
}

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

// The reading position as an EDITABLE box — a second VIEW of the one `n` (the slider is
// the other). It never filters; committing just calls onCommit(n), which re-queries the
// fence exactly like a slider drag. Commit is Enter/blur only (never per-keystroke), so a
// half-typed value can't flash an out-of-range graph; on commit we clamp to [1, M].
function ChapterBox({
  n,
  max,
  onCommit,
}: {
  n: number;
  max: number;
  onCommit: (v: number) => void;
}): JSX.Element {
  const [draft, setDraft] = useState(String(n));
  const [editing, setEditing] = useState(false);

  const commit = (): void => {
    const raw = draft.trim();
    if (!/^-?\d+$/.test(raw)) {
      setDraft(String(n)); // non-integer / empty / garbage -> reject, revert, no fence change
      setEditing(false);
      return;
    }
    const clamped = Math.min(max, Math.max(1, parseInt(raw, 10))); // 0/neg/>M -> nearest valid
    setDraft(String(clamped));
    setEditing(false);
    if (clamped !== n) onCommit(clamped);
  };

  return (
    <span className="reading-num">
      <span className="rn-label">chapter</span>
      <input
        className="chapter-box"
        type="text"
        inputMode="numeric"
        aria-label="Current chapter — type a number and press Enter"
        value={editing ? draft : String(n)}
        onFocus={() => {
          setEditing(true);
          setDraft(String(n));
        }}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur(); // blur runs commit
          else if (e.key === "Escape") {
            setDraft(String(n));
            setEditing(false);
            e.currentTarget.blur();
          }
        }}
      />
      <span className="of">of {max}</span>
    </span>
  );
}

// The min-connections view filter: hide background props with few links so the hubs read
// clearly. PURE DISPLAY — it never re-queries or touches the fence, only hides a subset of
// already-fenced nodes. Default-ON at DEFAULT_MIN_DEGREE so the graph opens on its
// connected core; − steps down to "all" (0 = every node back), + hides more. Stepped −/+
// so it can't land on a half-typed value.
function DegreeFilter({
  value,
  max,
  onChange,
}: {
  value: number;
  max: number;
  onChange: (v: number) => void;
}): JSX.Element {
  return (
    <span className="degree-filter" role="group" aria-label="Minimum connections filter">
      <span className="df-label">min links</span>
      <button
        className="df-btn"
        aria-label="Show more (lower the minimum)"
        disabled={value <= 0}
        onClick={() => onChange(Math.max(0, value - 1))}
      >
        −
      </button>
      <span className="df-value" aria-live="polite">
        {value === 0 ? "all" : value}
      </span>
      <button
        className="df-btn"
        aria-label="Hide more (raise the minimum)"
        disabled={value >= max}
        onClick={() => onChange(Math.min(max, value + 1))}
      >
        +
      </button>
    </span>
  );
}

// Salience demotion toggle: hide/show the generic common-noun "characters" (background).
// Default hidden; the count tells the user there's demoted detail, not absence. PURE VIEW —
// reversible, never persisted, every node still reachable.
function BackgroundToggle({
  hidden,
  count,
  onToggle,
}: {
  hidden: boolean;
  count: number;
  onToggle: () => void;
}): JSX.Element {
  return (
    <button
      className="bg-toggle"
      aria-pressed={!hidden}
      onClick={onToggle}
      title="Generic common-noun characters (e.g. ‘policeman’, ‘soldier’) — distinct background people, demoted from the default view."
    >
      <span className="bg-dot" aria-hidden />
      {hidden ? `show background (${count})` : "hide background"}
    </button>
  );
}

export default function App(): JSX.Element {
  const [works, setWorks] = useState<WorkModel[]>([]);
  const [work, setWork] = useState<WorkModel | null>(null);
  const [composing, setComposing] = useState(false);
  const [appending, setAppending] = useState(false);
  const [n, setN] = useState(1);
  const [minDegree, setMinDegree] = useState(DEFAULT_MIN_DEGREE);
  const [hideBackground, setHideBackground] = useState(true);
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
    setMinDegree(DEFAULT_MIN_DEGREE); // open on the clean connected core; "all" reveals every node
    setHideBackground(true); // open with generic common-noun characters demoted; toggle reveals them
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

  // Part B: degree is computed CLIENT-SIDE from the already-fenced payload — the filter
  // only ever hides a subset of revealed nodes, never changes what the fence returned.
  const degreeOf = useMemo(() => {
    const m = new Map<string, number>();
    for (const nd of elements.nodes) m.set(nd.data.id, 0);
    for (const e of elements.edges) {
      m.set(e.data.source, (m.get(e.data.source) ?? 0) + 1);
      m.set(e.data.target, (m.get(e.data.target) ?? 0) + 1);
    }
    return m;
  }, [elements]);
  const maxDegree = useMemo(
    () => elements.nodes.reduce((mx, nd) => Math.max(mx, degreeOf.get(nd.data.id) ?? 0), 0),
    [elements, degreeOf],
  );
  // How many revealed nodes are background (generic common-noun characters) — drives the
  // toggle label so the user knows there's hidden detail, not absence.
  const backgroundCount = useMemo(
    () => elements.nodes.filter((nd) => isBackground(nd.data.type, nd.data.label)).length,
    [elements],
  );
  // Both view filters compose into ONE hidden set (degree threshold + salience demotion);
  // each is independently reversible. Pure client-side over the fenced payload.
  const hiddenIds = useMemo(() => {
    const s = new Set<string>();
    for (const nd of elements.nodes) {
      const lowDegree = minDegree > 0 && (degreeOf.get(nd.data.id) ?? 0) < minDegree;
      const background = hideBackground && isBackground(nd.data.type, nd.data.label);
      if (lowDegree || background) s.add(nd.data.id);
    }
    return s;
  }, [elements, degreeOf, minDegree, hideBackground]);
  const visible = useMemo(
    () => ({
      nodes: counts.nodes - hiddenIds.size,
      edges: elements.edges.filter(
        (e) => !hiddenIds.has(e.data.source) && !hiddenIds.has(e.data.target),
      ).length,
    }),
    [counts, elements, hiddenIds],
  );
  const filtering = hiddenIds.size > 0;

  // Keep the threshold in range as the graph changes size with the slider (a sparse early
  // chapter has a lower max degree) — never leaves the user stuck on an all-hidden view.
  // Guarded on maxDegree > 0 so the default isn't stomped to 0 in the empty frame between
  // entering a work and its first fenced payload arriving (elements EMPTY ⇒ maxDegree 0).
  useEffect(() => {
    if (maxDegree > 0 && minDegree > maxDegree) setMinDegree(maxDegree);
  }, [maxDegree, minDegree]);

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
            <span>
              {filtering ? `${visible.nodes} of ${counts.nodes}` : counts.nodes} entities
            </span>
            <span>
              {filtering ? `${visible.edges} of ${counts.edges}` : counts.edges} links
            </span>
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
          <GraphView elements={elements} onSelect={onSelect} hiddenIds={hiddenIds} />
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
        <ChapterBox n={n} max={max} onCommit={setN} />
        <DegreeFilter value={minDegree} max={maxDegree} onChange={setMinDegree} />
        {backgroundCount > 0 ? (
          <BackgroundToggle
            hidden={hideBackground}
            count={backgroundCount}
            onToggle={() => setHideBackground((v) => !v)}
          />
        ) : null}
      </footer>
    </div>
  );
}
