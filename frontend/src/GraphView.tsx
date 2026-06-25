import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { Core, ElementDefinition, NodeSingular } from "cytoscape";
import cola from "cytoscape-cola";
import type { GraphElements, GraphNodeData, GraphEdgeData } from "./types";
import {
  EDGE_QUIET,
  GROUND,
  INK,
  INK_DIM,
  IDENTITY_RELATIONS,
  REVEAL,
  relationLabel,
  typeColor,
} from "./ontology";

cytoscape.use(cola);

export type Selection =
  | { kind: "node"; data: GraphNodeData }
  | { kind: "edge"; data: GraphEdgeData }
  | null;

interface Props {
  elements: GraphElements;
  onSelect: (sel: Selection) => void;
}

const reducedMotion =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// One constellation. Colours are hex (Cytoscape's canvas cannot parse oklch). Tiers
// read off edge `tier`; identity edges are the gold signature. Focus/dim classes drive
// the Obsidian hover behaviour; smooth via opacity transitions.
const STYLE: cytoscape.StylesheetStyle[] = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      "border-width": 1.5,
      "border-color": GROUND,
      width: "data(size)",
      height: "data(size)",
      label: "data(label)",
      color: INK,
      "font-family": "IBM Plex Sans, system-ui, sans-serif",
      "font-size": 11,
      "font-weight": 500,
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 6,
      "text-outline-color": GROUND,
      "text-outline-width": 2.4,
      "min-zoomed-font-size": 7,
      "transition-property": "opacity, border-color, border-width",
      "transition-duration": 160,
      "overlay-opacity": 0,
    },
  },
  {
    selector: "node.focus",
    style: { "border-color": INK, "border-width": 2.5 },
  },
  {
    selector: "edge",
    style: {
      "curve-style": "bezier",
      "target-arrow-shape": "none",
      width: 1,
      "line-color": EDGE_QUIET,
      color: INK_DIM,
      "font-family": "IBM Plex Sans, system-ui, sans-serif",
      "font-size": 8.5,
      "text-rotation": "autorotate",
      "text-background-color": GROUND,
      "text-background-opacity": 0.9,
      "text-background-padding": "2",
      "transition-property": "opacity, width, line-color",
      "transition-duration": 160,
      "overlay-opacity": 0,
    },
  },
  // Tier-2 social — medium presence.
  { selector: "edge[tier = 2]", style: { width: 1.7, "line-color": "#5b6488" } },
  // Tier-3 identity — the bold gold filament, always labelled (the signature).
  {
    selector: "edge[tier = 3]",
    style: {
      width: 2.6,
      "line-color": REVEAL,
      label: "data(rlabel)",
      color: REVEAL,
      "z-index": 10,
    },
  },
  // A neighbourhood edge in focus shows its relation; everything else stays quiet.
  { selector: "edge.focus", style: { label: "data(rlabel)", "line-color": INK_DIM, color: INK } },
  { selector: "node.dim", style: { opacity: 0.12 } },
  { selector: "edge.dim", style: { opacity: 0.06 } },
];

function colaLayout(): cytoscape.LayoutOptions {
  return {
    name: "cola",
    animate: !reducedMotion, // animate the settle, then STOP (no infinite drift)
    infinite: false,
    fit: false,
    randomize: false,
    nodeSpacing: () => 26,
    edgeLength: (e: { data: (k: string) => unknown }) => (e.data("tier") === 3 ? 150 : 110),
    maxSimulationTime: reducedMotion ? 800 : 2200,
    convergenceThreshold: 0.01,
  } as unknown as cytoscape.LayoutOptions;
}

function nodeSize(deg: number): number {
  return Math.round(20 + 8 * Math.sqrt(deg));
}

function toCyElements(elements: GraphElements): ElementDefinition[] {
  const nodes: ElementDefinition[] = elements.nodes.map((n) => ({
    group: "nodes",
    data: { ...n.data, color: typeColor(n.data.type), size: 22 },
  }));
  const edges: ElementDefinition[] = elements.edges.map((e) => ({
    group: "edges",
    data: { ...e.data, rlabel: relationLabel(e.data.relation) },
    classes: IDENTITY_RELATIONS.has(e.data.relation) ? "identity" : undefined,
  }));
  return [...nodes, ...edges];
}

export default function GraphView({ elements, onSelect }: Props): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const layoutRef = useRef<cytoscape.Layouts | null>(null);
  const firstFit = useRef(true);

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      style: STYLE,
      // 2.5x the old 0.2 — wheel zoom felt sluggish; 0.5 is responsive but still
      // smooth (cytoscape default is 1.0, which overshoots). Keeps zoom-to-cursor.
      wheelSensitivity: 0.5,
      minZoom: 0.3,
      maxZoom: 2.6,
    });

    const focusOn = (node: NodeSingular): void => {
      const hood = node.closedNeighborhood();
      cy.batch(() => {
        cy.elements().addClass("dim");
        hood.removeClass("dim").addClass("focus");
      });
    };
    const clearFocus = (): void => {
      cy.batch(() => cy.elements().removeClass("dim focus"));
    };
    cy.on("mouseover", "node", (e) => focusOn(e.target));
    cy.on("mouseout", "node", clearFocus);
    cy.on("tap", "node", (e) => onSelect({ kind: "node", data: e.target.data() }));
    cy.on("tap", "edge", (e) => onSelect({ kind: "edge", data: e.target.data() }));
    cy.on("tap", (e) => {
      if (e.target === cy) onSelect(null);
    });

    cyRef.current = cy;
    if (import.meta.env.DEV) (window as unknown as { __cy?: Core }).__cy = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [onSelect]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const desired = toCyElements(elements);
    const desiredIds = new Set(desired.map((e) => String(e.data.id)));
    const presentIds = new Set(cy.elements().map((e) => e.id()));

    const gone = cy.elements().filter((e) => !desiredIds.has(e.id()));
    if (gone.length > 0) gone.remove();
    const additions = desired.filter((e) => !presentIds.has(String(e.data.id)));
    const newIds = new Set(additions.map((e) => String(e.data.id)));
    if (additions.length > 0) cy.add(additions);
    if (additions.length === 0 && gone.length === 0) return;

    // Size every node by degree (Obsidian-style weighting), recomputed as links arrive.
    cy.batch(() => {
      cy.nodes().forEach((n) => {
        n.data("size", nodeSize(n.degree(false)));
      });
      additions.forEach((a) => {
        cy.getElementById(String(a.data.id)).style("opacity", 0);
      });
    });

    layoutRef.current?.stop();
    const layout = cy.layout(colaLayout());
    layoutRef.current = layout;
    // Fit exactly when the layout settles — no drift, no timing guess.
    const pad = firstFit.current ? 80 : 90;
    firstFit.current = false;
    layout.one("layoutstop", () => {
      const c = cyRef.current;
      if (c && c.elements().length > 0) {
        c.animate({ fit: { eles: c.elements(), padding: pad } }, { duration: 420 });
      }
    });
    layout.run();

    // Bloom the newcomers in; identity edges ignite (gold width pulse).
    cy.elements().forEach((ele) => {
      if (!newIds.has(ele.id())) return;
      if (reducedMotion) {
        ele.style("opacity", 1);
        return;
      }
      const identity = ele.isEdge() && ele.data("tier") === 3;
      ele.animate({ style: { opacity: 1 } }, { duration: identity ? 760 : 460 });
      if (identity) {
        ele.animate({ style: { width: 7 } }, { duration: 260 }).animate(
          { style: { width: 2.6 } },
          { duration: 520 },
        );
      }
    });

  }, [elements]);

  return <div ref={containerRef} className="graph-canvas" />;
}
