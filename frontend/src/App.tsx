import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchGraph, fetchWorks } from "./api";
import type { GraphElements, WorkModel } from "./types";
import { NODE_TYPES, TYPE_COLOR, relationLabel } from "./ontology";
import GraphView, { type Selection } from "./GraphView";

const EMPTY: GraphElements = { nodes: [], edges: [] };

function Cover({ work, onEnter }: { work: WorkModel | null; onEnter: () => void }): JSX.Element {
  return (
    <div className="cover">
      <div className="cover-inner">
        <div className="eyebrow">a spoiler-aware map of a story</div>
        <h1 className="wordmark">
          Story<span className="weave">Weave</span>
        </h1>
        <p className="cover-lede">
          The graph shows only what a reader knows by a given chapter. Slide forward and
          the story’s connections appear — a hidden identity igniting the moment the text
          earns it.
        </p>
        <button className="enter" onClick={onEnter} disabled={!work}>
          Enter <span className="enter-work">{work?.title ?? "…"}</span>
          <span className="enter-meta">from chapter 1</span>
        </button>
      </div>
    </div>
  );
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

export default function App(): JSX.Element {
  const [work, setWork] = useState<WorkModel | null>(null);
  const [entered, setEntered] = useState(false);
  const [n, setN] = useState(1);
  const [elements, setElements] = useState<GraphElements>(EMPTY);
  const [sel, setSel] = useState<Selection>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWorks()
      .then((works) => setWork(works.find((w) => w.slug === "the-hollow-crown") ?? works[0] ?? null))
      .catch((e: unknown) => setError(String(e)));
  }, []);

  // Every slider move RE-QUERIES the server at N. The fence is server-side, so the
  // payload itself only holds revealed-at-N data — the client never post-filters.
  useEffect(() => {
    if (!work || !entered) return;
    let live = true;
    fetchGraph(work.slug, n)
      .then((g) => live && setElements(g.elements))
      .catch((e: unknown) => setError(String(e)));
    return () => {
      live = false;
    };
  }, [work, n, entered]);

  const onSelect = useCallback((s: Selection) => setSel(s), []);
  const max = work?.chapter_count ?? 1;
  const counts = useMemo(
    () => ({ nodes: elements.nodes.length, edges: elements.edges.length }),
    [elements],
  );

  if (!entered) return <Cover work={work} onEnter={() => setEntered(true)} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="star">✦</span>
          <span className="mark">StoryWeave</span>
          <span className="work">{work?.title}</span>
        </div>
        <div className="readout">
          <span>ch {n}</span>
          <span>{counts.nodes} entities</span>
          <span>{counts.edges} links</span>
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
