import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { Core, ElementDefinition } from "cytoscape";
import type { GraphElements, GraphNodeData, GraphEdgeData } from "./types";
import { IDENTITY_RELATIONS, typeColor } from "./ontology";

export type Selection =
  | { kind: "node"; data: GraphNodeData }
  | { kind: "edge"; data: GraphEdgeData }
  | null;

interface Props {
  elements: GraphElements;
  onSelect: (sel: Selection) => void;
}

// The graph holds ONLY what the server revealed at N. Advancing N adds elements; we
// diff against what is already on screen and BLOOM the newcomers in — identity edges
// (the reveals) get the loud treatment, everything else stays quiet.
const STYLE: cytoscape.StylesheetStyle[] = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      "border-width": 1,
      "border-color": "oklch(0.30 0.02 260)",
      width: "mapData(importance, 0, 1, 16, 52)",
      height: "mapData(importance, 0, 1, 16, 52)",
      label: "data(label)",
      color: "oklch(0.88 0.02 80)",
      "font-family": "Iowan Old Style, Palatino, Georgia, serif",
      "font-size": 11,
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 5,
      "text-wrap": "wrap",
      "text-max-width": "120",
      "overlay-opacity": 0,
    },
  },
  {
    selector: "node:selected",
    style: { "border-width": 2, "border-color": "oklch(0.92 0.04 80)" },
  },
  {
    selector: "edge",
    style: {
      width: 1.1,
      "line-color": "oklch(0.42 0.02 260)",
      "curve-style": "bezier",
      "target-arrow-shape": "none",
      "overlay-opacity": 0,
    },
  },
  {
    // Tier-3 identity edges — the showcase. Distinct, labelled, brighter.
    selector: "edge.identity",
    style: {
      width: 2.4,
      "line-color": "oklch(0.82 0.12 85)",
      "line-style": "solid",
      label: "data(relation)",
      color: "oklch(0.86 0.06 85)",
      "font-family": "Iowan Old Style, Palatino, Georgia, serif",
      "font-size": 9,
      "text-rotation": "autorotate",
      "text-background-color": "oklch(0.16 0.02 260)",
      "text-background-opacity": 0.85,
      "text-background-padding": "2",
    },
  },
];

const LAYOUT: cytoscape.LayoutOptions = {
  name: "cose",
  animate: true,
  animationDuration: 520,
  randomize: false,
  fit: true,
  padding: 48,
  nodeRepulsion: () => 9000,
  idealEdgeLength: () => 110,
} as cytoscape.LayoutOptions;

function toCyElements(elements: GraphElements): ElementDefinition[] {
  const nodes: ElementDefinition[] = elements.nodes.map((n) => ({
    group: "nodes",
    data: { ...n.data, color: typeColor(n.data.type) },
  }));
  const edges: ElementDefinition[] = elements.edges.map((e) => ({
    group: "edges",
    data: { ...e.data },
    classes: IDENTITY_RELATIONS.has(e.data.relation) ? "identity" : undefined,
  }));
  return [...nodes, ...edges];
}

function bloom(cy: Core, newIds: Set<string>): void {
  cy.batch(() => {
    cy.elements().forEach((ele) => {
      if (newIds.has(ele.id())) ele.style("opacity", 0);
    });
  });
  cy.elements().forEach((ele) => {
    if (!newIds.has(ele.id())) return;
    const isIdentity = ele.isEdge() && ele.hasClass("identity");
    ele.animate({ style: { opacity: 1 } }, { duration: isIdentity ? 700 : 420 });
    if (isIdentity) {
      // The signature pulse: a brief widen-and-settle as the reveal lands.
      ele
        .animate({ style: { width: 6 } }, { duration: 240 })
        .animate({ style: { width: 2.4 } }, { duration: 460 });
    }
  });
}

export default function GraphView({ elements, onSelect }: Props): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  // Init once.
  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      style: STYLE,
      wheelSensitivity: 0.2,
      minZoom: 0.3,
      maxZoom: 2.5,
    });
    cy.on("tap", "node", (evt) => onSelect({ kind: "node", data: evt.target.data() }));
    cy.on("tap", "edge", (evt) => onSelect({ kind: "edge", data: evt.target.data() }));
    cy.on("tap", (evt) => {
      if (evt.target === cy) onSelect(null);
    });
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [onSelect]);

  // Sync to the fenced payload for the current N: remove what's gone, bloom what's new.
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

    if (additions.length > 0 || gone.length > 0) {
      cy.layout(LAYOUT).run();
      if (additions.length > 0) bloom(cy, newIds);
    }
  }, [elements]);

  return <div ref={containerRef} className="graph-canvas" />;
}
