import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchGraph, fetchWorks } from "./api";
import type { GraphElements, WorkModel } from "./types";
import { NODE_TYPES, TYPE_COLOR } from "./ontology";
import GraphView, { type Selection } from "./GraphView";

const EMPTY: GraphElements = { nodes: [], edges: [] };

function Legend(): JSX.Element {
  return (
    <div className="legend" aria-label="Node type legend">
      {NODE_TYPES.map((t) => (
        <span className="legend-item" key={t}>
          <span className="swatch" style={{ background: TYPE_COLOR[t] }} />
          {t}
        </span>
      ))}
    </div>
  );
}

function DetailPanel({ sel }: { sel: Selection }): JSX.Element | null {
  if (!sel) return null;
  if (sel.kind === "node") {
    const d = sel.data;
    const props = Object.entries(d.properties);
    return (
      <aside className="detail">
        <div className="detail-kind">{d.subtype ? `${d.type} · ${d.subtype}` : d.type}</div>
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
                    <span className="pk">{k}:</span> {v}
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
  return (
    <aside className="detail">
      <div className="detail-kind">tier {d.tier} relation</div>
      <h2>{d.relation}</h2>
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
  const [n, setN] = useState(1);
  const [elements, setElements] = useState<GraphElements>(EMPTY);
  const [sel, setSel] = useState<Selection>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWorks()
      .then((works) => {
        const hc = works.find((w) => w.slug === "the-hollow-crown") ?? works[0] ?? null;
        setWork(hc);
      })
      .catch((e: unknown) => setError(String(e)));
  }, []);

  // Every slider move RE-QUERIES the server at N — the fence is server-side, so the
  // payload itself only contains revealed-at-N data. The client never post-filters.
  useEffect(() => {
    if (!work) return;
    let live = true;
    fetchGraph(work.slug, n)
      .then((g) => {
        if (live) setElements(g.elements);
      })
      .catch((e: unknown) => setError(String(e)));
    return () => {
      live = false;
    };
  }, [work, n]);

  const onSelect = useCallback((s: Selection) => setSel(s), []);
  const max = work?.chapter_count ?? 1;
  const counts = useMemo(
    () => ({ nodes: elements.nodes.length, edges: elements.edges.length }),
    [elements],
  );

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark">StoryWeave</span>
          <span className="work">{work?.title ?? "…"}</span>
        </div>
        <div className="readout">
          revealed through chapter <b>{n}</b> · {counts.nodes} entities · {counts.edges} links
        </div>
      </header>

      <main className="stage">
        {error ? (
          <div className="error">
            {error}
            <div className="hint">Is the API running? `uvicorn storyweave.api.app:app`</div>
          </div>
        ) : (
          <GraphView elements={elements} onSelect={onSelect} />
        )}
        <Legend />
        <DetailPanel sel={sel} />
      </main>

      <footer className="slider-bar">
        <label htmlFor="chapter">Chapter</label>
        <input
          id="chapter"
          type="range"
          min={1}
          max={max}
          step={1}
          value={n}
          onChange={(e) => setN(Number(e.target.value))}
        />
        <output className="chapter-num">
          {n} <span className="of">/ {max}</span>
        </output>
      </footer>
    </div>
  );
}
