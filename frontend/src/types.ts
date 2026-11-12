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
  // R4/R6 fields. All optional because the frozen Hollow Crown payload predates them and
  // must keep rendering byte-for-byte (integration rule I2).
  weight?: number;
  /** "STATED" (the book says it in one sentence) or "INFERRED" (implied by context). */
  grade?: string | null;
  /** The verbatim sentence. Rule 4: every served edge carries one. */
  quote?: string | null;
  quote_chapter?: number | null;
  kin_role?: string | null;
  subtype?: string | null;
}

/** The cast dial. Mirrors the API's `cast` pattern `^(20|50|all)$`. */
export type CastSize = "20" | "50" | "all";

/** One row of the ego endpoint: how the focused entity relates to one neighbour.
 *  Mirrors schemas.py's EgoNeighbourModel exactly. */
export interface EgoNeighbour {
  entity_id: number;
  name: string;
  type: string;
  relation: string;
  grade: string | null;
  /** False for the symmetric relations, which must not be drawn or read with an arrow. */
  directed: boolean;
  /** True when the focused entity is the SOURCE — i.e. read the relation forwards. */
  outgoing: boolean;
  quote: string | null;
  quote_chapter: number | null;
  weight: number;
}

export interface EgoEntity {
  id: number;
  name: string;
  type: string;
  subtype: string | null;
  importance: number;
  first_seen_chapter: number;
  revealed_chapter: number;
  extraction_method: string;
  evidence_span: string | null;
}

export interface EgoResponse {
  slug: string;
  n: number;
  entity: EgoEntity;
  neighbours: EgoNeighbour[];
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

// D6/F6 (integration phase): a named chapter-range arc. `name` is null when the
// reader's bookmark hasn't reached `start_chapter` yet — the server redacts it
// (query/fence.py's visible_arcs), never the client; a work with none configured
// returns an empty array.
export interface ArcModel {
  ordinal: number;
  name: string | null;
  start_chapter: number;
  end_chapter: number;
}

export interface ArcsResponse {
  slug: string;
  n: number;
  arcs: ArcModel[];
}
