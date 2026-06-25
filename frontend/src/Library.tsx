import type { WorkModel } from "./types";
import { DEMO_SLUG } from "./ontology";

// The entry view: a two-column hero — the wordmark thesis on the left, the shelf of
// stories on the right — so the page reads as a composed spread, not a lonely centered
// column. Each user novel can be deleted (the CC0 demo is protected). Quiet by design;
// the boldness is spent inside the graph.

function WorkCard({
  work,
  onEnter,
  onDelete,
}: {
  work: WorkModel;
  onEnter: (w: WorkModel) => void;
  onDelete: (w: WorkModel) => void;
}): JSX.Element {
  const isDemo = work.slug === DEMO_SLUG;
  return (
    <div className="work-card">
      <button className="work-card-open" onClick={() => onEnter(work)}>
        <span className="work-card-title">{work.title}</span>
        <span className="work-card-meta">
          {work.chapter_count} {work.chapter_count === 1 ? "chapter" : "chapters"}
          {isDemo ? " · demo" : ""}
        </span>
        <span className="work-card-enter">Enter from chapter 1 →</span>
      </button>
      {isDemo ? (
        <span
          className="work-card-del disabled"
          title="The demo novel can’t be deleted — it’s the built-in sample."
          aria-hidden
        >
          🔒
        </span>
      ) : (
        <button
          className="work-card-del"
          onClick={() => onDelete(work)}
          aria-label={`Delete ${work.title}`}
          title={`Delete ${work.title}`}
        >
          ×
        </button>
      )}
    </div>
  );
}

export default function Library({
  works,
  onEnter,
  onAdd,
  onDelete,
}: {
  works: WorkModel[];
  onEnter: (w: WorkModel) => void;
  onAdd: () => void;
  onDelete: (w: WorkModel) => void;
}): JSX.Element {
  return (
    <div className="cover library">
      <div className="library-inner">
        <section className="lib-hero">
          <div className="eyebrow">a spoiler-aware map of a story</div>
          <h1 className="wordmark">
            Story<span className="weave">Weave</span>
          </h1>
          <p className="cover-lede">
            The graph shows only what a reader knows by a given chapter. Pick a story,
            slide forward, and its connections appear — a hidden identity igniting the
            moment the text earns it.
          </p>
          <div className="lib-hero-meta">
            <span className="hero-stat">8 entity types</span>
            <span className="hero-dot">·</span>
            <span className="hero-stat">reveal-fenced</span>
            <span className="hero-dot">·</span>
            <span className="hero-stat">fully local</span>
          </div>
        </section>

        <section className="lib-shelf">
          <div className="shelf-label">Your shelf</div>
          <div className="shelf">
            {works.map((w) => (
              <WorkCard key={w.slug} work={w} onEnter={onEnter} onDelete={onDelete} />
            ))}
            <button className="work-card work-card-add" onClick={onAdd}>
              <span className="work-card-plus">+</span>
              <span className="work-card-title add">Add a novel</span>
              <span className="work-card-meta">paste chapters, build its map</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
