// Wire shapes — mirror storyweave/api/schemas.py exactly. The client only ever
// receives data already fenced server-side at chapter N (nothing later).

export interface WorkModel {
  id: number;
  slug: string;
  title: string;
  chapter_count: number;
}

export interface GraphNodeData {
  id: string;
  label: string;
  type: string;
  subtype: string | null;
  importance: number;
  first_seen_chapter: number;
  revealed_chapter: number;
  extraction_method: string;
  evidence_span: string | null;
  properties: Record<string, string>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  relation: string;
  tier: number;
  first_seen_chapter: number;
  revealed_chapter: number;
  extraction_method: string;
  evidence_span: string | null;
}

export interface GraphElements {
  nodes: { data: GraphNodeData }[];
  edges: { data: GraphEdgeData }[];
}

export interface GraphResponse {
  slug: string;
  n: number;
  elements: GraphElements;
}
