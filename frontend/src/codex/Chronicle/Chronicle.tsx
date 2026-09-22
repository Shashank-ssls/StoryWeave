import { useEffect, useMemo, useRef, useState } from "react";
import type { WorkRoute } from "../../router/useHashRoute";
import type { GraphElements } from "../../types";
import { useWorkTitle } from "../useWorkTitle";
import Tabs from "../../components/Tabs/Tabs";
import Button from "../../components/Button/Button";
import { ChevronLeftIcon, ChevronRightIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { tabItems, navigateToTab } from "../tabs";
import { roman } from "../chapter/roman";
import { useChapter } from "../chapter/ChapterProvider";
import StateCard from "../states/StateCard";
import { navigate } from "../../router/useHashRoute";
import { buildViewModel, IDENTITY_COPY, tieLabel } from "../../graph/viewModel";
import { identityEndpoints, type CastSize } from "../../graph/stemmaModel";
import { chronicleRows, columnLayout, identityTimeline, stitches, type ChronicleRow } from "../../graph/chronicleModel";
import type { Reveal } from "../../graph/diff";
import styles from "./Chronicle.module.css";

// DESIGN_SPEC.md §6.4 Chronicle — the timeline. Unlike Dossier/Stemma there is no left
// rail: a 76px header bar carries the tabs instead. All row/thread/stitch/link data comes
// from the R3 chapter model's fenced payload for the bookmark (first_seen_chapter and
// revealed_chapter are static per-node/edge fields, already present in that ONE payload);
// only the identity timeline's "did this pair deepen" rule needs earlier chapters, which
// `ChapterProvider.ensureHistory` backfills into the same cache F8 already reads.

const ROW_H = 64;
const HEADER_ROW_H = 40;
const NAME_COL = 200;

function threadStyle(row: ChronicleRow, idEndpoints: Set<string>): { cls: string | undefined; dashed: boolean } {
  if (row.group === "person") {
    const principal = row.node.degree >= 2 || idEndpoints.has(row.node.id);
    return { cls: principal ? styles.threadInk : styles.threadDim, dashed: false };
  }
  return { cls: styles.threadFaint, dashed: true };
}

function sentenceOf(reveal: Reveal, byId: Map<string, { label: string }>, onOpen: (id: string) => void): JSX.Element {
  const copy = IDENTITY_COPY[reveal.edge.relation] ?? IDENTITY_COPY.ALIAS!;
  const aLabel = byId.get(reveal.edge.source)?.label ?? "?";
  const bLabel = byId.get(reveal.edge.target)?.label ?? "?";
  const parts = copy.sentence.split(/(\{a\}|\{b\})/);
  return (
    <>
      {parts.map((p, i) => {
        if (p === "{a}") return <button key={i} type="button" className={styles.link} onClick={() => onOpen(reveal.edge.source)}>{aLabel}</button>;
        if (p === "{b}") return <button key={i} type="button" className={styles.link} onClick={() => onOpen(reveal.edge.target)}>{bLabel}</button>;
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

export default function Chronicle({ route }: { route: WorkRoute }): JSX.Element {
  const title = useWorkTitle();
  const m = useChapter();
  const [cast, setCast] = useState<CastSize>("principal");
  const [selectedIndex, setSelectedIndex] = useState(-1);
  // R9 §11: below 1280 the right panel becomes a bottom sheet toggle drawer.
  const [panelOpen, setPanelOpen] = useState(false);
  useEffect(() => {
    if (!panelOpen) return;
    const onKey = (e: KeyboardEvent): void => { if (e.key === "Escape") setPanelOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panelOpen]);
  const [historyVersion, setHistoryVersion] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrolledFor = useRef<number | null>(null);

  const vm = useMemo(() => (m.data ? buildViewModel(m.data) : null), [m.data]);

  // R7: backfill every chapter 1..bookmark into the shared cache so the identity timeline
  // (which needs to see chapters BEFORE the bookmark to detect a deepening pair) is
  // complete. F1-safe: ensureHistory never asks for anything above the bookmark.
  useEffect(() => {
    let live = true;
    void m.ensureHistory(m.bookmark).then(() => {
      if (live) setHistoryVersion((v) => v + 1);
    });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m.bookmark, m.slug]);

  const history = useMemo(() => {
    const map = new Map<number, GraphElements>();
    for (let k = 1; k <= m.bookmark; k++) {
      const p = m.getCachedPayload(k);
      if (p) map.set(k, p);
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m.bookmark, historyVersion]);

  const rows = useMemo(() => (vm ? chronicleRows(vm, cast) : []), [vm, cast]);
  const rowIndex = useMemo(() => new Map(rows.map((r, i) => [r.node.id, i])), [rows]);
  const idEndpoints = useMemo(() => (vm ? identityEndpoints(vm) : new Set<string>()), [vm]);
  const layout = useMemo(() => columnLayout(m.bookmark, m.arcs), [m.bookmark, m.arcs]);
  const stitchList = useMemo(() => (vm ? stitches(vm, new Set(rows.map((r) => r.node.id))) : []), [vm, rows]);
  const timeline = useMemo(() => identityTimeline(history, m.bookmark), [history, m.bookmark]);

  // Default selection: the most recently revealed identity, reset whenever the bookmark
  // moves (a fresh view of the book). The reader's own click (below) overrides it until then.
  useEffect(() => {
    setSelectedIndex(timeline.length > 0 ? timeline.length - 1 : -1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m.bookmark, timeline.length]);

  // Opens already scrolled to the bookmark (§6.4 item 3) — once per bookmark, not on every
  // re-render (the reader may have scrolled away deliberately since). Deferred a frame:
  // right after mount the scroll container's own clientWidth can still reflect a pre-layout
  // size (fonts/rows not yet settled), which under-scrolls and leaves the sealed band just
  // off-screen — a real bug caught by comparing the 1440 and 1280 shots against each other.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || scrolledFor.current === m.bookmark) return;
    const raf = requestAnimationFrame(() => {
      el.scrollLeft = Math.max(0, layout.totalWidth - el.clientWidth);
      scrolledFor.current = m.bookmark;
    });
    return () => cancelAnimationFrame(raf);
    // `vm` is a real dependency, not a lint appeasement: the bookmark (and so
    // `layout.totalWidth`) updates BEFORE `data`/`vm` does (ChapterProvider sets the
    // bookmark synchronously, then commits data once the fetch resolves — see
    // ChapterProvider.tsx), so the scrollArea/svg don't exist in the DOM yet on the render
    // where this effect first sees the new bookmark. Without `vm` here, the effect never
    // fires again once the chart actually mounts, because its other two dependencies never
    // change a second time — found live: `scrollLeft` stayed 0 even though the effect had
    // "run" (with a null ref) for the correct bookmark already.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout.totalWidth, m.bookmark, vm]);

  const open = (id: string): void => navigate({ name: "work-entity", slug: route.slug, entityId: id });
  const selected = selectedIndex >= 0 ? timeline[selectedIndex] ?? null : null;
  const totalHeight = HEADER_ROW_H + Math.max(rows.length, 1) * ROW_H;
  const failedWithNothing = m.data === null && (m.banner !== null || m.workError);

  const explain = (reveal: Reveal): string => {
    if (reveal.kind === "deepen" && reveal.previousEdge) {
      return fillTemplate(codexTheme.chronicleExplainDeepen, { a: roman(reveal.previousEdge.revealed_chapter) });
    }
    if (!vm) return "";
    const a = vm.byId.get(reveal.edge.source)?.first_seen_chapter ?? reveal.edge.first_seen_chapter;
    const b = vm.byId.get(reveal.edge.target)?.first_seen_chapter ?? reveal.edge.first_seen_chapter;
    const [lo, hi] = a <= b ? [a, b] : [b, a];
    return fillTemplate(codexTheme.chronicleExplain, { a: roman(lo), b: roman(hi) });
  };

  return (
    <div className={styles.chronicle} data-testid="chronicle-root">
      <header className={styles.headerBar} data-testid="chronicle-header">
        <div className={styles.titleBlock}>
          <div className={styles.novelTitle}>{title}</div>
          <div className={styles.subtitle}>{codexTheme.chronicleSubtitle}</div>
        </div>
        <div className={styles.headerRight}>
          <Tabs items={tabItems} activeKey="chronicle" onChange={(k) => navigateToTab(k, route)} />
          <Button variant="outline" className={styles.panelToggle} onClick={() => setPanelOpen((v) => !v)} aria-expanded={panelOpen} data-testid="panel-toggle">
            {codexTheme.showChronicleDetail}
          </Button>
        </div>
      </header>

      <div
        className={`${styles.panelScrim} ${panelOpen ? styles.panelOpen : ""}`}
        onMouseDown={() => setPanelOpen(false)}
        data-testid="panel-scrim"
      />

      <div className={styles.body}>
        {failedWithNothing ? (
          <div className={styles.chart}>
            <StateCard
              testId="state-error"
              label={codexTheme.stateError.label}
              headline={codexTheme.stateError.headline}
              body={codexTheme.stateError.body}
              actions={
                m.banner && (
                  <Button variant="outline" onClick={() => m.requestChapter(m.banner?.failed ?? m.bookmark)} data-testid="state-retry">
                    {codexTheme.tryAgain}
                  </Button>
                )
              }
            />
          </div>
        ) : !vm ? (
          <div className={styles.chart}>
            <StateCard
              testId="skeleton"
              label={codexTheme.stateLoading.label}
              headline={codexTheme.stateLoading.headline}
              body={fillTemplate(codexTheme.stateLoading.body, { n: roman(m.loading ?? m.bookmark) })}
              loading
            />
          </div>
        ) : (
          <>
            <div className={styles.chart} data-testid="chronicle-chart">
              <div className={styles.castRow}>
                <span className={styles.castLabel}>{codexTheme.chronicleCastSizeLabel}</span>
                <div className={styles.segmented} role="radiogroup" aria-label={codexTheme.chronicleCastSizeLabel}>
                  {(["principal", "everyone"] as const).map((k) => (
                    <button
                      key={k}
                      type="button"
                      role="radio"
                      aria-checked={cast === k}
                      className={`${styles.segment} ${cast === k ? styles.segmentOn : ""}`}
                      onClick={() => setCast(k)}
                      data-testid={`chronicle-cast-${k}`}
                    >
                      {k === "principal" ? codexTheme.castPrincipal : codexTheme.castEveryone}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.chartBody}>
                <div className={styles.nameCol} style={{ width: NAME_COL }}>
                  <div className={styles.nameHeaderSpacer} style={{ height: HEADER_ROW_H }} />
                  {rows.map((r) => (
                    <div
                      key={r.node.id}
                      className={`${styles.nameRow} ${r.group === "person" ? styles.namePerson : styles.nameOther}`}
                      style={{ height: ROW_H }}
                      data-testid="chronicle-row"
                      data-entity={r.node.id}
                      data-group={r.group}
                    >
                      {r.node.label}
                    </div>
                  ))}
                </div>

                <div className={styles.scrollArea} ref={scrollRef} data-testid="chronicle-scroll">
                  <svg
                    className={styles.svg}
                    width={layout.totalWidth}
                    height={totalHeight}
                    data-testid="chronicle-svg"
                    role="img"
                    aria-label={codexTheme.chronicleSubtitle}
                  >
                    {layout.mode === "small"
                      ? Array.from({ length: m.bookmark }, (_, i) => i + 1).map((n) => (
                          <text
                            key={n}
                            x={layout.colX(n) + layout.colWidth / 2}
                            y={HEADER_ROW_H / 2 + 5}
                            textAnchor="middle"
                            className={n === m.bookmark ? styles.colHeaderOn : styles.colHeader}
                          >
                            {roman(n)}
                          </text>
                        ))
                      : layout.bands.map((band) => (
                          <g key={band.label}>
                            <line x1={band.x} x2={band.x} y1={0} y2={totalHeight} className={styles.bandRule} />
                            <text x={band.x + 4} y={16} className={styles.bandLabel}>{band.label}</text>
                          </g>
                        ))}

                    {/* sealed band — F3: exactly one column-width, regardless of remaining length */}
                    <rect
                      x={layout.sealedX}
                      y={HEADER_ROW_H}
                      width={layout.sealedWidth}
                      height={totalHeight - HEADER_ROW_H}
                      className={styles.sealedRect}
                      data-testid="chronicle-sealed"
                      data-width={layout.sealedWidth}
                    />
                    <text
                      x={layout.sealedX + layout.sealedWidth / 2}
                      y={HEADER_ROW_H + (totalHeight - HEADER_ROW_H) / 2}
                      textAnchor="middle"
                      className={styles.sealedLabel}
                      transform={
                        layout.mode === "large"
                          ? `rotate(-90 ${layout.sealedX + layout.sealedWidth / 2} ${HEADER_ROW_H + (totalHeight - HEADER_ROW_H) / 2})`
                          : undefined
                      }
                    >
                      {codexTheme.chronicleSealed}
                    </text>

                    {/* bookmark line + label */}
                    <line x1={layout.sealedX} x2={layout.sealedX} y1={HEADER_ROW_H} y2={totalHeight} className={styles.bookmarkLine} data-testid="chronicle-bookmark-line" />
                    <text x={layout.sealedX - 6} y={16} textAnchor="end" className={styles.bookmarkLabel}>
                      {fillTemplate(codexTheme.chronicleBookmarkLabel, { n: roman(m.bookmark) })}
                    </text>

                    {/* selected reveal's accent-soft capsule */}
                    {selected && rowIndex.has(selected.edge.source) && rowIndex.has(selected.edge.target) && (
                      <rect
                        x={layout.colX(selected.edge.revealed_chapter)}
                        width={layout.colWidth}
                        y={HEADER_ROW_H + Math.min(rowIndex.get(selected.edge.source)!, rowIndex.get(selected.edge.target)!) * ROW_H}
                        height={(Math.abs(rowIndex.get(selected.edge.source)! - rowIndex.get(selected.edge.target)!) + 1) * ROW_H}
                        className={styles.selectedCapsule}
                        data-testid="chronicle-selected-capsule"
                      />
                    )}

                    {/* presence threads */}
                    {rows.map((r, i) => {
                      const y = HEADER_ROW_H + i * ROW_H + ROW_H / 2;
                      const x1 = layout.colX(Math.max(1, r.node.first_seen_chapter));
                      const style = threadStyle(r, idEndpoints);
                      return (
                        <g key={r.node.id}>
                          <line x1={x1} x2={layout.sealedX} y1={y} y2={y} className={style.cls} strokeDasharray={style.dashed ? "2 4" : undefined} data-testid="chronicle-thread" data-entity={r.node.id} />
                          <circle cx={x1} cy={y} r={5} className={style.cls} data-role="dot" />
                        </g>
                      );
                    })}

                    {/* ties — thin curved stitches */}
                    {stitchList.map((s) => {
                      const ia = rowIndex.get(s.a);
                      const ib = rowIndex.get(s.b);
                      if (ia === undefined || ib === undefined) return null;
                      const x = layout.colX(s.chapter) + layout.colWidth / 2;
                      const yA = HEADER_ROW_H + ia * ROW_H + ROW_H / 2;
                      const yB = HEADER_ROW_H + ib * ROW_H + ROW_H / 2;
                      return (
                        <path
                          key={s.edge.id}
                          d={`M ${x} ${yA} Q ${x + 16} ${(yA + yB) / 2} ${x} ${yB}`}
                          className={styles.stitch}
                          strokeDasharray={s.dotted ? "2 4" : undefined}
                          data-testid="chronicle-stitch"
                          data-edge={s.edge.id}
                        >
                          <title>{fillTemplate(codexTheme.chronicleTieTooltip, { rel: tieLabel(s.edge.relation), n: roman(s.chapter) })}</title>
                        </path>
                      );
                    })}

                    {/* identity links */}
                    {timeline.map((reveal, idx) => {
                      const ia = rowIndex.get(reveal.edge.source);
                      const ib = rowIndex.get(reveal.edge.target);
                      if (ia === undefined || ib === undefined) return null;
                      const x = layout.colX(reveal.edge.revealed_chapter) + layout.colWidth / 2;
                      const yA = HEADER_ROW_H + ia * ROW_H + ROW_H / 2;
                      const yB = HEADER_ROW_H + ib * ROW_H + ROW_H / 2;
                      const copy = IDENTITY_COPY[reveal.edge.relation] ?? IDENTITY_COPY.ALIAS!;
                      // Flip the label to the left of the line once it's close enough to
                      // the sealed band that a right-hand label would run into it.
                      const labelLeft = x > layout.sealedX - 90;
                      return (
                        <g
                          key={`${reveal.edge.id}-${reveal.kind}`}
                          className={styles.identityLink}
                          onClick={() => setSelectedIndex(idx)}
                          data-testid="chronicle-identity-link"
                          data-edge={reveal.edge.id}
                          data-kind={reveal.kind}
                        >
                          <title>{fillTemplate(codexTheme.chronicleIdentityTooltip, { kicker: copy.kicker, n: roman(reveal.edge.revealed_chapter) })}</title>
                          <line x1={x} x2={x} y1={yA} y2={yB} className={styles.identityLine} />
                          <circle cx={x} cy={yA} r={3} className={styles.ringDotInner} />
                          <circle cx={x} cy={yA} r={6} className={styles.ringDotOuter} />
                          <circle cx={x} cy={yB} r={3} className={styles.ringDotInner} />
                          <circle cx={x} cy={yB} r={6} className={styles.ringDotOuter} />
                          <text x={labelLeft ? x - 8 : x + 8} y={(yA + yB) / 2} textAnchor={labelLeft ? "end" : "start"} className={styles.identityLabel}>{copy.short}</text>
                        </g>
                      );
                    })}
                  </svg>
                </div>
              </div>
            </div>

            <aside className={`${styles.rightPanel} ${panelOpen ? styles.panelOpen : ""}`} data-testid="chronicle-right-panel">
              <div className={styles.panel} data-testid="chronicle-reveal">
                {selected && vm ? (
                  <>
                    <div className={styles.kickerAccent}>
                      {fillTemplate(codexTheme.chronicleReveal, {
                        kicker: (IDENTITY_COPY[selected.edge.relation] ?? IDENTITY_COPY.ALIAS!).kicker,
                        n: roman(selected.edge.revealed_chapter),
                      })}
                    </div>
                    <h2 className={styles.panelTitle}>{sentenceOf(selected, vm.byId, open)}</h2>
                    <blockquote className={styles.panelQuote} data-testid="chronicle-reveal-quote">“{selected.edge.evidence_span}”</blockquote>
                    <p className={styles.explain} data-testid="chronicle-reveal-explain">{explain(selected)}</p>
                    {timeline.length > 1 && (
                      <div className={styles.pager} data-testid="chronicle-pager">
                        <Button
                          variant="icon"
                          aria-label={codexTheme.chroniclePrevReveal}
                          disabled={selectedIndex <= 0}
                          onClick={() => setSelectedIndex((i) => i - 1)}
                          data-testid="chronicle-reveal-prev"
                        >
                          <ChevronLeftIcon size={16} />
                        </Button>
                        <span>{fillTemplate(codexTheme.chronicleRevealOf, { i: selectedIndex + 1, n: timeline.length })}</span>
                        <Button
                          variant="icon"
                          aria-label={codexTheme.chronicleNextReveal}
                          disabled={selectedIndex >= timeline.length - 1}
                          onClick={() => setSelectedIndex((i) => i + 1)}
                          data-testid="chronicle-reveal-next"
                        >
                          <ChevronRightIcon size={16} />
                        </Button>
                      </div>
                    )}
                  </>
                ) : (
                  <p className={styles.noReveals} data-testid="chronicle-no-reveals">{codexTheme.chronicleNoReveals}</p>
                )}
                <div className={styles.panelSpacer} />
                {m.bookmark < m.chapterCount && (
                  <Button
                    variant="primary"
                    className={styles.readOn}
                    onClick={() => m.openDialog(m.bookmark + 1)}
                    data-testid="chronicle-read-on"
                  >
                    {fillTemplate(codexTheme.chronicleReadOn, { n: roman(m.bookmark + 1) })}
                  </Button>
                )}
              </div>
            </aside>
          </>
        )}
      </div>
    </div>
  );
}
