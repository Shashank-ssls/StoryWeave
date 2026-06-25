import { useState } from "react";
import { searchWork } from "./api";
import type { SearchResponse } from "./types";

// Fenced search, in the stage. The query runs at the current reading position n, so the
// answer + passages can only quote text revealed by chapter n — search obeys the same
// fence as the graph. Closed by default; opened from the top bar.

export default function SearchPanel({
  slug,
  n,
  onClose,
}: {
  slug: string;
  n: number;
  onClose: () => void;
}): JSX.Element {
  const [q, setQ] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (): Promise<void> => {
    const query = q.trim();
    if (!query) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await searchWork(slug, n, query));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="search-panel" role="search">
      <div className="search-head">
        <span className="search-title">Ask the story</span>
        <button className="search-x" onClick={onClose} aria-label="Close search">
          ×
        </button>
      </div>
      <div className="search-as-of">answered as of chapter {n} — nothing later</div>
      <label className="search-q-label" htmlFor="search-q">
        Ask a question
      </label>
      <div className="search-bar">
        <input
          id="search-q"
          className="search-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void run()}
          placeholder="Who is the Gray Sparrow really?"
          autoFocus
        />
        <button className="search-go" onClick={() => void run()} disabled={loading || !q.trim()}>
          {loading ? "…" : "Ask"}
        </button>
      </div>

      {error ? <div className="search-error">{error}</div> : null}

      {result ? (
        result.hits.length === 0 ? (
          <div className="search-empty">
            Nothing revealed by chapter {n} answers that yet. Read on and ask again.
          </div>
        ) : (
          <div className="search-results">
            <p className="search-answer">{result.answer}</p>
            <ul className="search-hits">
              {result.hits.map((h) => (
                <li className="search-hit" key={h.chunk_id}>
                  <span className="hit-ch">ch {h.chapter_ordinal}</span>
                  <span className="hit-text">{h.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )
      ) : null}
    </aside>
  );
}
