import { useEffect, useRef } from "react";
import cytoscape, { type ElementDefinition } from "cytoscape";
import { codexStyle } from "../../graph/codexStyle";
import type { ViewModel } from "../../graph/viewModel";
import { nodeSize } from "../../graph/stemmaModel";
import { cyRegistry } from "../../graph/cyRegistry";

// DESIGN_SPEC.md §6.1 Landing — the try-it panel's mini graph: "non-interactive except
// hover", rendered from the SAME view model the rest of the app builds from the fenced
// payload. F9: the caller passes only the current chapter's `ViewModel` (never anything
// prefetched), so there is nothing here to draw beyond what the reader has confirmed —
// the fence holds by construction, exactly like the Dossier's ego graph (R4).
export default function MiniGraph({ vm, className }: { vm: ViewModel; className?: string }): JSX.Element {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    const els: ElementDefinition[] = [
      ...vm.nodes.map((n) => ({
        group: "nodes" as const,
        data: { id: n.id, label: n.label, display: n.label, kind: n.kind, degree: n.degree, initial: n.initial, size: nodeSize(n), sizeFar: nodeSize(n) * 0.8 },
        classes: n.kind !== "person" ? "italic" : "",
      })),
      ...vm.edges.map((e) => ({
        group: "edges" as const,
        data: { id: e.id, source: e.source, target: e.target, kind: e.kind, relation: e.relation, revealed_chapter: e.revealed_chapter },
      })),
    ];
    const cy = cytoscape({
      container: container.current,
      elements: els,
      style: codexStyle,
      userZoomingEnabled: false,
      userPanningEnabled: false,
      boxSelectionEnabled: false,
      autoungrabify: true,
    });
    cyRegistry.instances += 1;
    cyRegistry.created += 1;
    container.current.dataset.nodes = cy.nodes().map((n) => n.id()).join(",");
    container.current.dataset.edges = cy.edges().map((e) => e.id()).join(",");
    cy.layout({ name: "concentric", concentric: (n: cytoscape.NodeSingular) => n.degree(false), minNodeSpacing: 22, padding: 16, animate: false } as cytoscape.LayoutOptions).run();
    cy.fit(undefined, 12);
    return () => {
      cy.destroy();
      cyRegistry.instances -= 1;
    };
  }, [vm]);

  return <div ref={container} className={className} data-testid="landing-mini-graph" />;
}
