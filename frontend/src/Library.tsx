import type { WorkModel } from "./types";

// The entry view: the wordmark thesis, then a shelf of stories. Each work is a star you
// can enter; "Add a novel" opens the composer. Quiet by design — the boldness is spent
// inside the graph, not here.

function WorkCard({ work, onEnter }: { work: WorkModel; onEnter: (w: WorkModel) => void }): JSX.Element {
  return (
    <button className="work-card" onClick={() => onEnter(work)}>
      <span className="work-card-title">{work.title}</span>
      <span className="work-card-meta">
        {work.chapter_count} {work.chapter_count === 1 ? "chapter" : "chapters"}
      </span>
      <span className="work-card-enter">Enter from chapter 1 →</span>
    </button>
  );
}

export default function Library({
  works,
  onEnter,
  onAdd,
}: {
  works: WorkModel[];
  onEnter: (w: WorkModel) => void;
  onAdd: () => void;
}): JSX.Element {
  return (
    <div className="cover library">
      <div className="library-inner">
        <div className="eyebrow">a spoiler-aware map of a story</div>
        <h1 className="wordmark">
          Story<span className="weave">Weave</span>
        </h1>
        <p className="cover-lede">
          The graph shows only what a reader knows by a given chapter. Pick a story, slide
          forward, and its connections appear — a hidden identity igniting the moment the
          text earns it.
        </p>

        <div className="shelf-label">Your shelf</div>
        <div className="shelf">
          {works.map((w) => (
            <WorkCard key={w.slug} work={w} onEnter={onEnter} />
          ))}
          <button className="work-card work-card-add" onClick={onAdd}>
            <span className="work-card-plus">+</span>
            <span className="work-card-title add">Add a novel</span>
            <span className="work-card-meta">paste chapters, build its map</span>
          </button>
        </div>
      </div>
    </div>
  );
}
