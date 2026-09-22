import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition, type Layouts } from "cytoscape";
import cola from "cytoscape-cola";
import { codexStyle, colaOptions, SETTLE_MS } from "../../graph/codexStyle";
import { cyRegistry } from "../../graph/cyRegistry";
import { declutterLabels, focusSet, labelRank, minorLabelIds, nodeSize, zoomTier, type VisibleGraph } from "../../graph/stemmaModel";

// The Stemma canvas (DESIGN_SPEC §6.3 canvas, §7, §8.3). Owns exactly one Cytoscape
// instance and at most one running cola layout for its lifetime; both are torn down in
// the unmount cleanup (tab switch and work switch unmount this component). Everything
// it draws arrives as an already-filtered `VisibleGraph` from stemmaModel — this file
// decides HOW things look, never WHAT is shown.

// cytoscape.use is not idempotent-safe across HMR; guard it.
const registered = new WeakSet<object>();
if (!registered.has(cytoscape)) {
  cytoscape.use(cola);
  registered.add(cytoscape);
}

export interface Selection {
  kind: "node" | "edge";
  id: string;
}

export interface EdgeHover {
  id: string;
  x: number;
  y: number;
}

export interface StemmaCanvasHandle {
  zoomIn(): void;
  zoomOut(): void;
  fitAll(): void;
  fitFocus(): void;
}

interface Props {
  graph: VisibleGraph;
  identityEndpoints: Set<string>;
  focusId: string | null;
  steps: 1 | 2;
  /** Hover-preview focus (§8.3): applied like the focus but never moves the camera. */
  previewId: string | null;
  selected: Selection | null;
  kbdId: string | null;
  /** R6 §8.2: the identity edge id mid-3s-highlight after a reveal closes, or null. Owned
   *  by RevealChrome (shared with the Dossier's equivalent highlight) — this canvas only
   *  plays the pulse while the id is set. */
  justRevealedEdgeId: string | null;
  reducedMotion: boolean;
  onNodeTap(id: string): void;
  onEdgeTap(id: string): void;
  onNodeDblTap(id: string): void;
  onBackgroundDblTap(): void;
  onNodeHover(id: string | null): void;
  onEdgeHover(h: EdgeHover | null): void;
  className?: string;
  focusNameClassName?: string;
}

const FIT_PADDING = 60;
const FIT_PADDING_LARGE = 30;
// R9: max ties framed by a focus fit before the camera prioritises by rank (see
// fitFocusNow) instead of trying to fit every neighbour a hub principal has.
const FIT_FOCUS_BUDGET = 12;
// R9: below this many TOTAL nodes on canvas, there's no legibility pressure at all (the
// budget above only matters for a hub with 13+ ties) — fit the whole connected web
// instead of just the near+focus set, so a dimmed "far" context node never lands clipped
// at the exact viewport edge (measured: Lady Veris half off the top edge on the 6-node
// Hollow Crown demo, because far-tier nodes sit outside the near-cluster's fit box).
const FIT_ALL_WHEN_SMALL = 20;
const TRANSITION_MS = 420; // mirrors codexStyle's node transition-duration
const FIT_MAX_ZOOM = 1.2; // a fit lands inside the default tier (0.5–1.5)
const USER_MAX_ZOOM = 3;

function toElements(graph: VisibleGraph, identityEndpoints: Set<string>): ElementDefinition[] {
  const els: ElementDefinition[] = [];
  const minor = minorLabelIds(graph.nodes, identityEndpoints);
  for (const n of graph.nodes) {
    const badge = graph.folded.get(n.id);
    const size = nodeSize(n);
    const isId = identityEndpoints.has(n.id);
    const classes = [
      n.kind !== "person" ? "italic" : "",
      isId ? "identity-endpoint" : "",
      minor.has(n.id) ? "label-minor" : "",
    ].filter(Boolean).join(" ");
    els.push({
      group: "nodes",
      data: { id: n.id, label: n.label, display: badge ? `${n.label} +${badge}` : n.label, kind: n.kind, degree: n.degree, initial: n.initial, size, sizeFar: size * 0.8 },
      classes,
    });
  }
  for (const e of graph.edges) {
    els.push({
      group: "edges",
      data: { id: e.id, source: e.source, target: e.target, kind: e.kind, relation: e.relation, revealed_chapter: e.revealed_chapter },
    });
  }
  return els;
}

const StemmaCanvas = forwardRef<StemmaCanvasHandle, Props>(function StemmaCanvas(props, ref) {
  const container = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const layoutRef = useRef<Layouts | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const refitOnStop = useRef(false); // data-driven bursts refit; drag-end bursts don't
  const settledRef = useRef(false); // true once this instance's first layout has stopped
  // Cytoscape/cola fire 'layoutstop' both on a natural settle AND when `.stop()` is called
  // to supersede a still-running layout with a newer one (runPhysics below does this on
  // every graph update). Without this guard, superseding a layout that's still mid-burst
  // spuriously consumes `refitOnStop`/`settledRef` meant for the NEW layout's real settle,
  // so the camera never gets its correct final fit — measured as the R6/R9 off-screen-focus
  // bug: a fresh Stemma mount whose focus resolves one render after the initial (no-focus)
  // graph triggers exactly this double-burst, and the wrong (mid-flight) fit is the one
  // that sticks. One flag per `.stop()` call, consumed by that stop alone.
  const suppressNextStop = useRef(false);
  // cytoscape-cola fires 'layoutstop' twice per burst for graphs small enough to hit its
  // internal convergenceThreshold early (measured, R9: 11ms into a run whose
  // maxSimulationTime is 950ms) — once on that early "convergence" stop, using positions
  // barely moved from the seed ring, and again when maxSimulationTime itself elapses, using
  // the actually-relaxed layout. The old code treated the FIRST stop as the real settle,
  // consuming refitOnStop/settledRef before the burst had visually finished — this is the
  // root cause of the camera-fit bug (a small post-navigation graph converges early, so the
  // "final" fit is computed from near-seed positions). Only the stop at/after the run's own
  // declared duration counts as the real settle; an earlier one is ignored outright.
  const layoutStartedAt = useRef(0);
  const layoutSettleMs = useRef(SETTLE_MS);

  // ---- lifecycle: one instance per mount, destroyed on unmount ----
  useEffect(() => {
    if (!container.current) return;
    const cy = cytoscape({
      container: container.current,
      style: codexStyle,
      minZoom: 0.2,
      maxZoom: 3,
      boxSelectionEnabled: false,
      selectionType: "single",
    });
    cyRef.current = cy;
    cyRegistry.instances += 1;
    cyRegistry.created += 1;
    cyRegistry.stemma = cy;
    settledRef.current = false;

    cy.on("layoutstart", () => { cyRegistry.layouts += 1; });
    cy.on("layoutstop", () => {
      cyRegistry.layouts -= 1;
      if (suppressNextStop.current) { suppressNextStop.current = false; return; }
      // A premature convergence-triggered stop (see layoutSettleMs above): ignore it, the
      // burst is still running and will report again at its real duration.
      if (performance.now() - layoutStartedAt.current < layoutSettleMs.current - 100) return;
      settledRef.current = true;
      declutter();
      if (refitOnStop.current) { refitOnStop.current = false; fitFocusNow(); }
    });

    // §7.5 zoom tiers
    const applyTier = (): void => {
      const tier = zoomTier(cy.zoom());
      cy.batch(() => {
        cy.nodes().removeClass("tier-far tier-close");
        if (tier === "far") cy.nodes().addClass("tier-far");
        else if (tier === "close") cy.nodes().addClass("tier-close");
      });
      container.current?.setAttribute("data-tier", tier);
    };
    cy.on("zoom", applyTier);
    applyTier();

    // Interaction: tap/dbltap/hover. Cytoscape's own selection is disabled in favour of
    // the app's `selected` prop so the panel and the canvas can never disagree.
    cy.on("tap", "node", (ev) => propsRef.current.onNodeTap(ev.target.id() as string));
    cy.on("tap", "edge", (ev) => propsRef.current.onEdgeTap(ev.target.id() as string));
    cy.on("dbltap", "node", (ev) => propsRef.current.onNodeDblTap(ev.target.id() as string));
    cy.on("dbltap", (ev) => { if (ev.target === cy) propsRef.current.onBackgroundDblTap(); });
    cy.on("mouseover", "node", (ev) => propsRef.current.onNodeHover(ev.target.id() as string));
    cy.on("mouseout", "node", () => propsRef.current.onNodeHover(null));
    cy.on("mouseover", "edge", (ev) => {
      const p = ev.target.midpoint();
      const r = { x: p.x * cy.zoom() + cy.pan().x, y: p.y * cy.zoom() + cy.pan().y };
      propsRef.current.onEdgeHover({ id: ev.target.id() as string, x: r.x, y: r.y });
    });
    cy.on("mouseout", "edge", () => propsRef.current.onEdgeHover(null));
    cy.on("tap", (ev) => { if (ev.target === cy) propsRef.current.onNodeHover(null); });

    return () => {
      layoutRef.current?.stop();
      layoutRef.current = null;
      if (declutterRaf.current) cancelAnimationFrame(declutterRaf.current);
      if (declutterTimer.current) window.clearTimeout(declutterTimer.current);
      cy.destroy();
      cyRef.current = null;
      cyRegistry.instances -= 1;
      if (cyRegistry.stemma === cy) cyRegistry.stemma = null;
    };
  }, []);

  // ---- data: diff-apply the visible graph, then (re)run cola ----
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const wanted = toElements(props.graph, props.identityEndpoints);
    const wantedIds = new Set(wanted.map((e) => e.data.id as string));
    cy.batch(() => {
      cy.elements().filter((el) => !wantedIds.has(el.id())).remove();
      const existing = new Set(cy.elements().map((el) => el.id()));
      const fresh = wanted.filter((e) => !existing.has(e.data.id as string));
      // New nodes are seeded on a ring around what's already there (radius grows with
      // the count) rather than piled at the centre: cola's finite burst then only has
      // to relax a sane start. Piling them up made it stack 100 nodes into a vertical
      // strip within the burst (measured at R5).
      if (fresh.length > 0) {
        const bb = cy.nodes().length ? cy.nodes().boundingBox() : { x1: 0, y1: 0, w: 0, h: 0 };
        const cxp = bb.x1 + bb.w / 2;
        const cyp = bb.y1 + bb.h / 2;
        const freshNodes = fresh.filter((e) => e.group === "nodes");
        const radius = Math.max(bb.w, bb.h) / 2 + 40 + 18 * Math.sqrt(freshNodes.length) * 3;
        freshNodes.forEach((e, i) => {
          const a = (i / freshNodes.length) * Math.PI * 2;
          e.position = { x: cxp + Math.cos(a) * radius, y: cyp + Math.sin(a) * radius };
        });
        cy.add(fresh);
      }
      for (const e of wanted) {
        const el = cy.getElementById(e.data.id as string);
        if (el.length) {
          el.data(e.data);
          el.classes(e.classes ?? "");
        }
      }
    });
    // The camera fits once the burst has settled (layoutstop), never mid-flight: a fit
    // taken while cola is still expanding lands at the wrong zoom (measured at R5: the
    // whole synthetic graph ended up as a far-tier speck after a 700ms-timer fit).
    refitOnStop.current = true;
    runPhysics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.graph, props.identityEndpoints, props.reducedMotion]);

  // ---- focus / preview / selection classes ----
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const activeFocus = props.previewId ?? props.focusId;
    cy.batch(() => {
      cy.elements().removeClass("focus near far selected-edge kbd-ring");
      if (activeFocus && cy.getElementById(activeFocus).length) {
        const set = focusSet(props.graph.edges, activeFocus, props.steps);
        cy.nodes().forEach((n) => { n.addClass(n.id() === activeFocus ? "focus" : set.has(n.id()) ? "near" : "far"); });
        cy.edges().forEach((e) => { e.addClass(set.has(e.source().id()) && set.has(e.target().id()) ? "near" : "far"); });
      }
      if (props.selected?.kind === "edge") cy.getElementById(props.selected.id).addClass("selected-edge");
      if (props.kbdId) cy.getElementById(props.kbdId).addClass("kbd-ring");
    });
    declutter(); // label set changed with the focus (focus initial / near labels) → re-resolve collisions
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.focusId, props.previewId, props.steps, props.selected, props.kbdId, props.graph]);

  // ---- R6 §8.2: 3s glow pulse on the just-revealed edge, once, on close ----
  useEffect(() => {
    const cy = cyRef.current;
    const id = props.justRevealedEdgeId;
    if (!cy || !id) return;
    const play = (): void => {
      const ele = cy.getElementById(id);
      if (ele.length === 0) return;
      ele.addClass("just-revealed");
      ele
        .animate({ style: { "underlay-opacity": 0.55, "underlay-padding": 12 } }, { duration: 500, easing: "ease-out" })
        .animate({ style: { "underlay-opacity": 0.15, "underlay-padding": 5 } }, { duration: 2500, easing: "ease-out" });
    };
    // Defer until the canvas's first layout has settled, so the pulse never animates a
    // style mid-burst. (Measured, R6: this does NOT fix the off-screen focus framing seen
    // right after "Return to The Stemma" — that reproduces identically from a PLAIN tab
    // click Dossier -> Stemma with no reveal involved at all, so it's a pre-existing R5
    // SPA-navigation camera-fit bug, not something this effect causes or fixes. Logged in
    // FRONTEND_OVERHAUL.md §9 as a BROKEN/open item, out of scope for R6.) Kept anyway
    // because animating mid-burst is still the wrong thing to do on its own merits.
    if (settledRef.current) play();
    else cy.one("layoutstop", play);
    return () => {
      cy.off("layoutstop", play);
      cy.getElementById(id).removeClass("just-revealed").stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.justRevealedEdgeId]);

  // ---- camera follows the REAL focus (never the hover preview) ----
  const lastFit = useRef<string>("");
  useEffect(() => {
    const key = `${props.focusId ?? ""}|${props.steps}`;
    if (key === lastFit.current) return;
    lastFit.current = key;
    fitFocusNow();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.focusId, props.steps]);

  // §7.2 label collision: after every settle, defer lower-ranked labels that would collide
  // (stemmaModel.declutterLabels). Boxes are model-space, so the result holds at any zoom;
  // deferred labels come back in the focus set and at the close tier, like minor ones.
  // Scheduled on the next frame: label boxes are measured from the last render, so a
  // label whose text just changed (the un-focused node: initial → name) is only sized
  // correctly once a frame has drawn it (measured at R5 as a 2px residual collision).
  const declutterRaf = useRef(0);
  function declutter(): void {
    const cy = cyRef.current;
    if (!cy) return;
    cy.forceRender();
    // Two frames: Cytoscape redraws on its own rAF loop, so a single rAF can run BEFORE
    // that redraw and still see the old text metrics (measured at R5: a 2px collision on
    // the just-un-focused hub). The second frame is after it.
    if (declutterRaf.current) cancelAnimationFrame(declutterRaf.current);
    declutterRaf.current = requestAnimationFrame(() => {
      declutterRaf.current = requestAnimationFrame(() => {
        declutterRaf.current = 0;
        declutterNow();
      });
    });
    // ...and once more after the 420ms size transition (codexStyle `transition-duration`):
    // an un-focused node shrinks from 46px, which moves its label ~8px (measured at R5 as
    // the last surviving collision).
    if (declutterTimer.current) window.clearTimeout(declutterTimer.current);
    declutterTimer.current = window.setTimeout(() => { declutterTimer.current = 0; declutterNow(); }, TRANSITION_MS + 40);
  }
  const declutterTimer = useRef(0);
  function declutterNow(): void {
    const cy = cyRef.current;
    if (!cy) return;
    const { graph, identityEndpoints } = propsRef.current;
    // Outside any batch: the boxes must reflect the labels as currently drawn (a
    // previously deferred label has an empty box until its class is gone, and the focus
    // node's box is its initial, not its name).
    cy.nodes().removeClass("label-deferred");
    const ranked = labelRank(graph.nodes, identityEndpoints)
      .map((n) => cy.getElementById(n.id))
      .filter((el) => el.length > 0 && el.style("label") !== "")
      .map((el) => ({ id: el.id(), box: el.boundingBox({ includeLabels: true, includeNodes: false, includeEdges: false, includeOverlays: false }) }));
    const deferred = declutterLabels(ranked);
    cy.batch(() => { for (const id of deferred) cy.getElementById(id).addClass("label-deferred"); });
  }

  // One finite cola burst (see colaOptions); any previous burst is stopped first so at
  // most one layout ever runs per instance.
  function runPhysics(): void {
    const cy = cyRef.current;
    if (!cy) return;
    if (layoutRef.current) {
      suppressNextStop.current = true;
      layoutRef.current.stop();
    }
    const reducedMotion = propsRef.current.reducedMotion;
    layoutStartedAt.current = performance.now();
    layoutSettleMs.current = reducedMotion ? 800 : SETTLE_MS;
    const layout = cy.layout(colaOptions(reducedMotion, cy.nodes().length) as unknown as cytoscape.LayoutOptions);
    layoutRef.current = layout;
    layout.run();
  }

  // Drag: the node is pinned by the user's hand while the burst runs; on release the
  // graph re-settles around where it was dropped.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const onDragFree = (): void => runPhysics();
    cy.on("dragfree", "node", onDragFree);
    return () => { cy.off("dragfree", "node", onDragFree); };
  }, []);

  // A fit never zooms past the default tier (§7.5): a 3-node focus set would otherwise
  // land at zoom 2+, with 34px nodes drawn at 70px. Cytoscape clamps `fit` to maxZoom,
  // so maxZoom is lowered for the duration of the fit only — user zoom keeps the full range.
  function animateFit(eles: cytoscape.CollectionReturnValue): void {
    const cy = cyRef.current;
    if (!cy) return;
    const dur = propsRef.current.reducedMotion ? 0 : 420;
    // Large casts get a tighter frame so the fit-all still lands in the default tier at
    // the 1280×720 minimum viewport (measured at R5: 0.44 with the 60px padding).
    const padding = eles.nodes().length > 40 ? FIT_PADDING_LARGE : FIT_PADDING;
    cy.maxZoom(FIT_MAX_ZOOM);
    cy.animate({ fit: { eles, padding } }, { duration: dur, complete: () => cy.maxZoom(USER_MAX_ZOOM) });
    if (dur === 0) cy.maxZoom(USER_MAX_ZOOM);
  }

  function fitFocusNow(): void {
    const cy = cyRef.current;
    if (!cy || cy.nodes().length === 0) return;
    const { focusId, steps } = propsRef.current;
    if (focusId && cy.getElementById(focusId).length) {
      if (cy.nodes().length <= FIT_ALL_WHEN_SMALL) {
        animateFit(fitAllTargets());
        return;
      }
      const set = focusSet(propsRef.current.graph.edges, focusId, steps);
      let fitTarget = cy.nodes().filter((n) => set.has(n.id()));
      if (set.size > FIT_FOCUS_BUDGET + 1) {
        // A large focus set (a hub's many ties) still DRAWS and LABELS every tie —
        // labelVisible's inFocusSet rule never hides them — but framing the camera to all
        // of them at once can't keep labels legible in a fixed viewport (measured, R9:
        // synthetic-100's hub principal, 22 near nodes, effective label size 8.7px at
        // 1280×720, under the 13px floor). Ranking by graph importance (degree/identity,
        // as the label budget does) does NOT shrink the frame here — a high-degree
        // neighbour's OTHER ties pull cola to place it far from the focus regardless of
        // its rank (measured: near-zero zoom change when tried). Distance in the settled
        // layout is what actually determines the frame size, so the camera fits the focus
        // node plus its FIT_FOCUS_BUDGET nearest (not most "important") ties; the rest
        // still draw, label and position normally, just possibly past the tight frame,
        // reachable by zooming out or panning.
        const focusPos = cy.getElementById(focusId).position();
        type Positioned = { id(): string; position(): { x: number; y: number } };
        const dist = (n: Positioned): number => {
          const p = n.position();
          return Math.hypot(p.x - focusPos.x, p.y - focusPos.y);
        };
        const nearestIds = (cy.nodes() as unknown as { toArray(): Positioned[] }).toArray()
          .filter((n) => set.has(n.id()) && n.id() !== focusId)
          .sort((a, b) => dist(a) - dist(b))
          .slice(0, FIT_FOCUS_BUDGET)
          .map((n) => n.id());
        const nearestSet = new Set([focusId, ...nearestIds]);
        fitTarget = cy.nodes().filter((n) => nearestSet.has(n.id()));
      }
      animateFit(fitTarget);
    } else {
      animateFit(fitAllTargets());
    }
  }

  // Fit-all frames the connected web. Cola drifts isolated nodes (no visible tie) far
  // out, and one stray dot would otherwise force the whole cast down to the far tier
  // (measured at R5); they stay drawn and reachable by zooming/panning.
  function fitAllTargets(): cytoscape.CollectionReturnValue {
    const cy = cyRef.current!;
    const connected = cy.nodes().filter((n) => n.degree(false) > 0);
    return connected.length >= 10 ? connected.union(connected.connectedEdges()) : cy.elements();
  }

  // The focus node's NAME (§7.1: Pirata One 24px below-right) — a Cytoscape node has one
  // label and the focus disk uses it for the initial, so the name is an HTML overlay that
  // tracks the node's rendered position.
  const nameRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const cy = cyRef.current;
    const el = nameRef.current;
    if (!cy || !el) return;
    let raf = 0;
    const update = (): void => {
      raf = 0;
      const id = propsRef.current.previewId ?? propsRef.current.focusId;
      const node = id ? cy.getElementById(id) : null;
      if (!node || node.length === 0) { el.hidden = true; return; }
      const p = node.renderedPosition();
      const r = (node.renderedWidth() / 2) * 0.75;
      el.hidden = false;
      el.textContent = node.data("label") as string;
      el.style.transform = `translate(${Math.round(p.x + r)}px, ${Math.round(p.y + r)}px)`;
    };
    const schedule = (): void => { if (!raf) raf = requestAnimationFrame(update); };
    cy.on("render viewport position", schedule);
    schedule();
    return () => { cy.off("render viewport position", schedule); if (raf) cancelAnimationFrame(raf); };
  }, [props.focusId, props.previewId]);

  useImperativeHandle(ref, () => ({
    zoomIn: () => zoomBy(1.25),
    zoomOut: () => zoomBy(0.8),
    fitAll: () => {
      if (cyRef.current) animateFit(fitAllTargets());
    },
    fitFocus: fitFocusNow,
  }));

  function zoomBy(factor: number): void {
    const cy = cyRef.current;
    if (!cy) return;
    const w = cy.width();
    const h = cy.height();
    cy.animate({ zoom: { level: cy.zoom() * factor, renderedPosition: { x: w / 2, y: h / 2 } } }, { duration: propsRef.current.reducedMotion ? 0 : 220 });
  }

  return (
    <div className={props.className}>
      <div ref={container} style={{ position: "absolute", inset: 0 }} data-testid="stemma-cy" />
      <div ref={nameRef} className={props.focusNameClassName} data-testid="focus-name" hidden />
    </div>
  );
});

export default StemmaCanvas;
