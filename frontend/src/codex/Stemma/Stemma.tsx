import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { navigate, routePath, type WorkRoute } from "../../router/useHashRoute";
import { useWorkTitle } from "../useWorkTitle";
import Tabs from "../../components/Tabs/Tabs";
import Button from "../../components/Button/Button";
import Input from "../../components/Input/Input";
import { MinusIcon, PlusIcon } from "../../icons";
import { codexTheme, fillTemplate } from "../theme";
import { tabItems, navigateToTab } from "../tabs";
import { roman } from "../chapter/roman";
import { useChapter } from "../chapter/ChapterProvider";
import StateCard from "../states/StateCard";
import { buildViewModel, principalOf, tieLabel } from "../../graph/viewModel";
import {
  identityEndpoints,
  neighboursOf,
  searchNames,
  SHOW_ALL,
  visibleGraph,
  type CastSize,
  type ShowFilter,
} from "../../graph/stemmaModel";
import StemmaCanvas, { type EdgeHover, type Selection, type StemmaCanvasHandle } from "./StemmaCanvas";
import SelectionPanel from "./SelectionPanel";
import styles from "./Stemma.module.css";

// DESIGN_SPEC.md §6.3 The Stemma — the full graph with focus mode (§8.3). All story data
// comes from the R3 chapter model's fenced payload; the rail filters and the search only
// ever see what is already in that payload (F4: a name not yet revealed simply does not
// exist here, so it can neither match nor be hinted at).

const HOVER_MS = 80;
const TOOLTIP_MAX = 80;

function isTypingTarget(t: EventTarget | null): boolean {
  return t instanceof HTMLElement && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
}

export default function Stemma({ route }: { route: WorkRoute }): JSX.Element {
  const title = useWorkTitle();
  const m = useChapter();
  const vm = useMemo(() => (m.data ? buildViewModel(m.data) : null), [m.data]);
  const principal = vm ? principalOf(vm) : null;
  const urlFocus = route.name === "work-web" ? route.focus : null;

  // undefined = not resolved yet (first data still loading); null = the reader cleared it.
  const [focusId, setFocusId] = useState<string | null | undefined>(undefined);
  const [steps, setSteps] = useState<1 | 2>(1);
  const [show, setShow] = useState<ShowFilter>(SHOW_ALL);
  const [cast, setCast] = useState<CastSize>("principal");
  const [selected, setSelected] = useState<Selection | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [kbdId, setKbdId] = useState<string | null>(null);
  const [hover, setHover] = useState<EdgeHover | null>(null);
  const [query, setQuery] = useState("");
  const canvas = useRef<StemmaCanvasHandle>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const hoverTimer = useRef<number | null>(null);

  const reducedMotion = useMemo(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);

  // ---- focus resolution: URL param → else principal; absent entity → principal, quietly ----
  useEffect(() => {
    if (!vm) return;
    const wanted = urlFocus && vm.byId.has(urlFocus) ? urlFocus : null;
    setFocusId((cur) => {
      let next: string | null;
      if (wanted && wanted !== cur) next = wanted; // URL names a present entity
      else if (cur === null) next = null; // explicitly cleared: stays cleared
      else if (cur && vm.byId.has(cur)) next = cur; // still present
      else next = principal?.id ?? null; // unresolved, or vanished at this chapter → principal, quietly
      if (next !== cur) {
        // A resolved focus (URL, default, or fallback) also fills the panel with that
        // node, exactly as a click would — the panel never shows a vanished entity.
        setSelected(next ? { kind: "node", id: next } : null);
      } else {
        setSelected((s) => (s && !(s.kind === "node" ? vm.byId.has(s.id) : vm.edges.some((e) => e.id === s.id)) ? null : s));
      }
      return next;
    });
    setKbdId(null);
  }, [vm, urlFocus, principal?.id]);

  // URL mirrors the focus (§8.3) — location.replace: no history entry, hashchange fires.
  useEffect(() => {
    if (!vm || focusId === undefined) return;
    const wanted = routePath({ name: "work-web", slug: route.slug, focus: focusId });
    if (window.location.hash !== wanted) window.location.replace(wanted);
  }, [focusId, route.slug, vm]);

  // The visible graph is recomputed on every focus change (the focus is always visible)
  // but only becomes a NEW object when its content changes — otherwise the canvas would
  // re-run physics and refit on every click.
  const graphRaw = useMemo(() => (vm ? visibleGraph(vm, { show, cast, focusId: focusId ?? null }) : null), [vm, show, cast, focusId]);
  const graphRef = useRef<{ key: string; value: typeof graphRaw }>({ key: "", value: null });
  const graph = useMemo(() => {
    const key = graphRaw
      ? `${graphRaw.nodes.map((n) => n.id).join(",")}|${graphRaw.edges.map((e) => e.id).join(",")}|${[...graphRaw.folded].map(([k, v]) => `${k}:${v}`).join(",")}`
      : "";
    if (key !== graphRef.current.key) graphRef.current = { key, value: graphRaw };
    return graphRef.current.value;
  }, [graphRaw]);
  const idEndpoints = useMemo(() => (vm ? identityEndpoints(vm) : new Set<string>()), [vm]);

  const openDossier = useCallback((id: string) => navigate({ name: "work-entity", slug: route.slug, entityId: id }), [route.slug]);

  const focusOn = useCallback((id: string | null): void => {
    setFocusId(id);
    setSelected(id ? { kind: "node", id } : null);
    setKbdId(null);
  }, []);

  const onNodeTap = useCallback((id: string): void => {
    if (id === focusId) focusOn(null); // clicking the focused node again clears (§8.3)
    else focusOn(id);
  }, [focusId, focusOn]);

  const onNodeHover = useCallback((id: string | null): void => {
    if (hoverTimer.current !== null) window.clearTimeout(hoverTimer.current);
    if (id === null) { setPreviewId(null); return; }
    hoverTimer.current = window.setTimeout(() => setPreviewId(id), HOVER_MS);
  }, []);

  // ---- keyboard (§8.3, §8.5): scoped by target guard, never inside inputs ----
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (m.dialog.open || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === "/" && !isTypingTarget(e.target)) { e.preventDefault(); searchRef.current?.focus(); return; }
      if (isTypingTarget(e.target)) return;
      if (e.key === "Escape") {
        e.preventDefault();
        if (selected && selected.kind === "edge") setSelected(null);
        else if (focusId) { focusOn(null); canvas.current?.fitAll(); }
        setKbdId(null);
        return;
      }
      if (!graph || !focusId) return;
      const nbs = neighboursOf(graph.edges, graph.nodes, focusId);
      if (nbs.length === 0) return;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        const i = kbdId ? nbs.indexOf(kbdId) : -1;
        setKbdId(nbs[(i + 1) % nbs.length] ?? null);
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        const i = kbdId ? nbs.indexOf(kbdId) : 0;
        setKbdId(nbs[(i - 1 + nbs.length) % nbs.length] ?? null);
      } else if (e.key === "Enter" && kbdId) {
        e.preventDefault();
        focusOn(kbdId);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [m.dialog.open, selected, focusId, graph, kbdId, focusOn]);

  // ---- search over fenced labels only ----
  const results = useMemo(() => (vm ? searchNames(vm, query).slice(0, 6) : []), [vm, query]);
  const noMatch = query.trim().length > 0 && results.length === 0;
  const pick = (id: string): void => { focusOn(id); setQuery(""); searchRef.current?.blur(); };

  const hoveredEdge = hover && vm ? vm.edges.find((e) => e.id === hover.id) ?? null : null;
  const tooltip = hoveredEdge
    ? {
        line: fillTemplate(codexTheme.tooltipTie, { rel: tieLabel(hoveredEdge.relation), n: roman(hoveredEdge.revealed_chapter) }),
        quote:
          hoveredEdge.kind === "identity" && hoveredEdge.evidence_span
            ? hoveredEdge.evidence_span.length > TOOLTIP_MAX ? `${hoveredEdge.evidence_span.slice(0, TOOLTIP_MAX)}…` : hoveredEdge.evidence_span
            : null,
      }
    : null;

  const focusNode = focusId && vm ? vm.byId.get(focusId) ?? null : null;

  return (
    <div className={styles.stemma} data-testid="stemma-root">
      <aside className={styles.rail} data-testid="stemma-rail">
        <a className={styles.wordmark} href={routePath({ name: "landing" })}>StoryWeave</a>
        <div className={styles.novelTitle}>{title}</div>

        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="stemma-search">{codexTheme.findNameLabel}</label>
          <Input
            id="stemma-search"
            ref={searchRef}
            className={styles.search}
            placeholder={codexTheme.findName}
            value={query}
            autoComplete="off"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && results[0]) pick(results[0].id);
              if (e.key === "Escape") { setQuery(""); searchRef.current?.blur(); }
            }}
            data-testid="stemma-search"
          />
          {results.length > 0 && (
            <ul className={styles.results} data-testid="search-results">
              {results.map((n) => (
                <li key={n.id}>
                  <button type="button" className={styles.resultRow} onClick={() => pick(n.id)} data-entity={n.id}>{n.label}</button>
                </li>
              ))}
            </ul>
          )}
          {noMatch && (
            <div className={styles.noMatch}>
              <StateCard
                testId="search-no-match"
                label={codexTheme.stateNoMatch.label}
                headline={fillTemplate(codexTheme.stateNoMatch.headline, { n: roman(m.bookmark) })}
                body={codexTheme.stateNoMatch.body}
              />
            </div>
          )}
        </div>

        <fieldset className={styles.fieldset}>
          <legend className={styles.fieldLabel}>{codexTheme.showLabel}</legend>
          {([["people", codexTheme.showPeople], ["orders", codexTheme.showOrders], ["places", codexTheme.showPlaces]] as const).map(([k, label]) => (
            <label key={k} className={styles.check}>
              <input type="checkbox" className={styles.checkbox} checked={show[k]} onChange={(e) => setShow({ ...show, [k]: e.target.checked })} data-testid={`show-${k}`} />
              {label}
            </label>
          ))}
        </fieldset>

        <div className={styles.field}>
          <div className={styles.fieldLabel}>{codexTheme.castSizeLabel}</div>
          <div className={styles.segmented} role="radiogroup" aria-label={codexTheme.castSizeLabel}>
            {(["principal", "everyone"] as const).map((k) => (
              <button
                key={k}
                type="button"
                role="radio"
                aria-checked={cast === k}
                className={`${styles.segment} ${cast === k ? styles.segmentOn : ""}`}
                onClick={() => setCast(k)}
                data-testid={`cast-${k}`}
              >
                {k === "principal" ? codexTheme.castPrincipal : codexTheme.castEveryone}
              </button>
            ))}
          </div>
          <p className={styles.caption}>{codexTheme.castCaption}</p>
        </div>

        <div className={styles.railSpacer} />
        {m.chapterCount > 0 && (
          <div className={styles.footer} data-testid="stemma-footer">
            {fillTemplate(codexTheme.readTo, { n: roman(m.bookmark), m: m.chapterCount })} ·{" "}
            <button type="button" className={styles.footerLink} onClick={() => m.openDialog()} data-testid="stemma-change">
              {codexTheme.changeLink}
            </button>
          </div>
        )}
      </aside>

      <div className={`${styles.canvas} web-canvas-mask`} data-testid="stemma-canvas">
        <div className={styles.canvasTopBar}>
          <span className={styles.focusLabel} data-testid="focus-label">
            {focusNode
              ? fillTemplate(codexTheme.focusedOn, { name: focusNode.label, steps: steps === 1 ? codexTheme.stepOne : codexTheme.stepTwo })
              : codexTheme.unfocused}
          </span>
          <Tabs items={tabItems} activeKey="web" onChange={(k) => navigateToTab(k, route)} />
        </div>

        <div className={styles.canvasBody}>
          {graph && (
            <StemmaCanvas
              ref={canvas}
              className={styles.cy}
              focusNameClassName={styles.focusName}
              graph={graph}
              identityEndpoints={idEndpoints}
              focusId={focusId ?? null}
              steps={steps}
              previewId={previewId}
              selected={selected}
              kbdId={kbdId}
              reducedMotion={reducedMotion}
              onNodeTap={onNodeTap}
              onEdgeTap={(id) => setSelected({ kind: "edge", id })}
              onNodeDblTap={openDossier}
              onBackgroundDblTap={() => canvas.current?.fitAll()}
              onNodeHover={onNodeHover}
              onEdgeHover={setHover}
            />
          )}
          {tooltip && hover && (
            <div className={styles.tooltip} style={{ left: hover.x, top: hover.y }} role="tooltip" data-testid="edge-tooltip">
              <div>{tooltip.line}</div>
              {tooltip.quote && <div className={styles.tooltipQuote}>“{tooltip.quote}”</div>}
            </div>
          )}
        </div>

        <div className={styles.controls}>
          {focusId && (
            <Button variant="outline" onClick={() => { focusOn(null); canvas.current?.fitAll(); }} data-testid="clear-focus">
              {codexTheme.clearFocus}
            </Button>
          )}
          <Button variant="outline" className={styles.zoomButton} aria-label={codexTheme.zoomIn} onClick={() => canvas.current?.zoomIn()} data-testid="zoom-in"><PlusIcon size={16} /></Button>
          <Button variant="outline" className={styles.zoomButton} aria-label={codexTheme.zoomOut} onClick={() => canvas.current?.zoomOut()} data-testid="zoom-out"><MinusIcon size={16} /></Button>
          {focusId && (
            <div className={styles.segmented} role="radiogroup" aria-label={codexTheme.stepsLabel} data-testid="steps">
              {([1, 2] as const).map((s) => (
                <button key={s} type="button" role="radio" aria-checked={steps === s} className={`${styles.segment} ${steps === s ? styles.segmentOn : ""}`} onClick={() => setSteps(s)} data-testid={`steps-${s}`}>
                  {s === 1 ? codexTheme.stepOne : codexTheme.stepTwo}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <aside className={styles.rightPanel} data-testid="stemma-right-panel">
        {vm && <SelectionPanel vm={vm} selected={selected} onOpen={openDossier} />}
      </aside>
    </div>
  );
}
