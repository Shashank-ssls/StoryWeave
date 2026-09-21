import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { codexStyle } from "../../graph/codexStyle";
import type { ViewModel } from "../../graph/viewModel";

// Dossier right-panel ego graph (DESIGN_SPEC §6.2 right panel, §7): the entity centred
// as the focus disk with its initial, 1-hop neighbours on a ring (`.near`), 2-hop faint
// (`.far`). `concentric` layout, not cola — stability over motion. Clicking a node opens
// its dossier. Only view-model elements are ever handed to Cytoscape, so the fence
// (F1-F3) holds here by construction: there is nothing else to draw.

const EGO_MAX = 40;

function egoElements(vm: ViewModel, focusId: string): { els: ElementDefinition[]; level: Map<string, number> } {
  const level = new Map<string, number>([[focusId, 3]]);
  const adj = new Map<string, Set<string>>();
  for (const e of vm.edges) {
    if (!adj.has(e.source)) adj.set(e.source, new Set());
    if (!adj.has(e.target)) adj.set(e.target, new Set());
    adj.get(e.source)!.add(e.target);
    adj.get(e.target)!.add(e.source);
  }
  for (const n1 of adj.get(focusId) ?? []) level.set(n1, 2);
  // 2-hop is context, not content: for a hub in a big cast it would be the whole book
  // and the fit would zoom labels out of legibility (seen on synthetic-100), so the
  // faint ring is only drawn while the whole ego set stays readable at panel size.
  const far = new Set<string>();
  for (const n1 of adj.get(focusId) ?? []) {
    for (const n2 of adj.get(n1) ?? []) if (!level.has(n2)) far.add(n2);
  }
  if (level.size + far.size <= EGO_MAX) for (const n2 of far) level.set(n2, 1);

  const els: ElementDefinition[] = [];
  for (const n of vm.nodes) {
    const lv = level.get(n.id);
    if (lv === undefined) continue;
    const cls = [lv === 3 ? "focus" : lv === 2 ? "near" : "far"];
    if (n.kind !== "person") cls.push("italic");
    els.push({
      group: "nodes",
      data: { id: n.id, label: n.label, kind: n.kind, degree: n.degree, initial: n.initial },
      classes: cls.join(" "),
    });
  }
  for (const e of vm.edges) {
    if (!level.has(e.source) || !level.has(e.target)) continue;
    const near = e.source === focusId || e.target === focusId;
    els.push({
      group: "edges",
      data: { id: e.id, source: e.source, target: e.target, kind: e.kind, relation: e.relation, revealed_chapter: e.revealed_chapter },
      classes: near ? "near" : "far",
    });
  }
  return { els, level };
}

export default function EgoGraph({
  vm,
  focusId,
  onOpen,
  className,
}: {
  vm: ViewModel;
  focusId: string;
  onOpen(id: string): void;
  className?: string;
}): JSX.Element {
  const container = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;

  useEffect(() => {
    if (!container.current) return;
    const { els, level } = egoElements(vm, focusId);
    const cy = cytoscape({
      container: container.current,
      elements: els,
      style: codexStyle,
      userZoomingEnabled: false,
      userPanningEnabled: false,
      boxSelectionEnabled: false,
      autoungrabify: true,
    });
    cyRef.current = cy;
    // Canvas content is invisible to the DOM, so the drawn element ids are mirrored as
    // data attributes: the fence E2E tests assert the ego graph against the fixtures.
    container.current.dataset.nodes = cy.nodes().map((n) => n.id()).join(",");
    container.current.dataset.edges = cy.edges().map((e) => e.id()).join(",");
    cy.layout({
      name: "concentric",
      concentric: (n) => level.get(n.id()) ?? 0,
      levelWidth: () => 1,
      minNodeSpacing: 28,
      padding: 24,
      animate: false,
    } as cytoscape.LayoutOptions).run();
    cy.on("tap", "node", (ev) => {
      const id = ev.target.id() as string;
      if (id !== focusId) onOpenRef.current(id);
    });
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [vm, focusId]);

  return <div ref={container} className={className} data-testid="ego-graph" />;
}
