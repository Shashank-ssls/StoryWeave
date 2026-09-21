// StoryWeave — Cytoscape stylesheet for "The Heretic's Codex" (DESIGN_SPEC.md §7).
// Reference implementation for the build chat; tune after screenshots.
//
// Expected element data (view model built client-side from the fenced /graph payload):
//   node.data: { id, label, kind: 'person'|'order'|'place'|'thing', degree, initial }
//   edge.data: { id, source, target, kind: 'social'|'structural'|'identity', relation, revealed_chapter }
// Classes the app toggles:
//   .focus (the focused node), .near (in focus set), .far (outside focus set),
//   .italic (orders/places/things labels), .selected-edge, .just-revealed (3s highlight)

export const T = {
  bg: '#150B0A', deep: '#0C0605', line: '#3A2420', ink: '#E8D8C2',
  dim: '#A8917D', faint: '#6B5548', accent: '#D9503A', onInk: '#150B0A',
};

const body = '"EB Garamond", Georgia, serif';
const display = '"Pirata One", Georgia, serif';

export const codexStyle = [
  // ---- nodes: base ----
  { selector: 'node', style: {
      'width': 16, 'height': 16,
      'background-color': T.bg, 'border-width': 1.4, 'border-color': T.ink,
      'label': 'data(label)', 'font-family': body, 'font-size': 17, 'color': T.ink,
      'text-valign': 'bottom', 'text-halign': 'center', 'text-margin-y': 8,
      'text-outline-color': T.bg, 'text-outline-width': 3,
      'min-zoomed-font-size': 9,
      'transition-property': 'background-color, border-color, color, width, height',
      'transition-duration': '420ms',
  }},
  { selector: 'node[kind = "person"]', style: {
      'shape': 'ellipse', 'background-color': T.ink, 'border-width': 0,
      'width': 'mapData(degree, 0, 30, 16, 34)', 'height': 'mapData(degree, 0, 30, 16, 34)',
  }},
  { selector: 'node[kind = "order"]', style: { 'shape': 'ellipse' } },
  { selector: 'node[kind = "place"]', style: { 'shape': 'rectangle' } },
  { selector: 'node[kind = "thing"]', style: { 'shape': 'diamond', 'width': 20, 'height': 20 } },
  { selector: 'node.italic', style: { 'font-style': 'italic' } },

  // ---- focus mode ----
  { selector: 'node.far', style: { 'color': T.faint, 'border-color': T.faint } },
  { selector: 'node.far[kind = "person"]', style: { 'background-color': T.faint } },
  { selector: 'node.focus', style: {
      'width': 46, 'height': 46, 'background-color': T.ink,
      'border-width': 7, 'border-color': T.bg,          // inner ring gap
      'outline-width': 1.5, 'outline-color': T.ink, 'outline-offset': 0,  // outer ring (Cytoscape >= 3.28; else use an underlay)
      'label': 'data(initial)', 'font-family': display, 'font-size': 22, 'color': T.onInk,
      'text-valign': 'center', 'text-margin-y': 0, 'text-outline-width': 0,
  }},

  // ---- edges ----
  { selector: 'edge', style: {
      'curve-style': 'straight', 'width': 1.2, 'line-color': T.line,
      'target-arrow-shape': 'none', 'label': '',
      'transition-property': 'line-color, width, opacity', 'transition-duration': '420ms',
  }},
  { selector: 'edge[kind = "social"].near', style: { 'line-color': T.dim, 'width': 1.4 } },
  { selector: 'edge[kind = "structural"]', style: { 'line-style': 'dashed', 'line-dash-pattern': [2, 4], 'width': 1 } },
  { selector: 'edge[kind = "identity"]', style: {
      'line-color': T.accent, 'width': 2.6,
      'underlay-color': T.accent, 'underlay-opacity': 0.15, 'underlay-padding': 5,
  }},
  { selector: 'edge[kind = "identity"].far', style: { 'opacity': 0.45 } },
  { selector: 'edge.selected-edge', style: { 'width': 3.2, 'underlay-opacity': 0.25 } },
  { selector: 'edge.just-revealed', style: { 'underlay-opacity': 0.35, 'underlay-padding': 8 } },
];

// Zoom tiers (§7.5): call on 'zoom' events.
export function applyZoomTier(cy) {
  const z = cy.zoom();
  cy.batch(() => {
    cy.nodes().removeClass('tier-far tier-close');
    if (z < 0.5) cy.nodes().addClass('tier-far');
    else if (z > 1.5) cy.nodes().addClass('tier-close');
  });
}
codexStyle.push(
  { selector: 'node.tier-far', style: { 'label': '' } },
  { selector: 'node.tier-far.focus, node.tier-far.identity-endpoint', style: { 'label': 'data(label)' } },
);

// Physics (§7.6)
export const colaOptions = (reducedMotion) => ({
  name: 'cola',
  animate: true,
  infinite: !reducedMotion,
  maxSimulationTime: reducedMotion ? 800 : 4000,
  nodeSpacing: 40,
  edgeLength: (e) => (e.data('kind') === 'identity' ? 110 : 140),
  convergenceThreshold: 0.01,
  fit: false,
});

// View-model rules (§7.1, §7.3): apply BEFORE handing elements to Cytoscape.
//  - drop nodes of type Title; drop Concept/Event unless the "Everyone" filter is on
//  - map Character->person, Organization->order, Place->place, Item|Ability->thing
//  - merge parallel edges: an identity edge absorbs any social edge between the same pair
//  - never add an identity edge that lacks its quote (mirror of the citation gate)
