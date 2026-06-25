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

export interface IngestResponse {
  slug: string;
  title: string;
  chapter_count: number;
  chunks_added: number;
  state: string;
}

export type AnalysisState = "queued" | "extracting" | "relating" | "ready" | "error" | "unknown";

export interface AnalysisStatus {
  slug: string;
  state: AnalysisState;
  detail: string;
  node_count: number;
}

export interface ChapterPreview {
  ordinal: number;
  title: string | null;
  is_new: boolean;
}

export interface PreviewResponse {
  chapters: ChapterPreview[];
  total: number;
  new_count: number;
}

export interface AppendResponse {
  slug: string;
  chapter_count: number;
  chapters_added: number;
  chunks_added: number;
  state: string;
}
