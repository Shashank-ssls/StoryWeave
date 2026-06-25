import type {
  AnalysisStatus,
  GraphResponse,
  IngestResponse,
  SearchResponse,
  WorkModel,
} from "./types";

// Thin typed client over the fenced FastAPI routes. `n` is mandatory on every data
// route (the server returns 422 without it) — the reading position is never optional.

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(await errorMessage(resp, url));
  }
  return (await resp.json()) as T;
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(await errorMessage(resp, url));
  }
  return (await resp.json()) as T;
}

// FastAPI puts the human-readable reason in `detail`; surface it instead of a bare code.
async function errorMessage(resp: Response, url: string): Promise<string> {
  try {
    const data = (await resp.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
  } catch {
    /* fall through to the status line */
  }
  return `${resp.status} ${resp.statusText} for ${url}`;
}

export async function fetchWorks(): Promise<WorkModel[]> {
  const data = await getJSON<{ works: WorkModel[] }>("/api/v1/works");
  return data.works;
}

export async function fetchGraph(slug: string, n: number): Promise<GraphResponse> {
  return getJSON<GraphResponse>(
    `/api/v1/works/${encodeURIComponent(slug)}/graph?n=${n}`,
  );
}

// In-app ingest: paste a novel, get back the new work + the launched analysis state.
export async function ingestWork(title: string, text: string): Promise<IngestResponse> {
  return postJSON<IngestResponse>("/api/v1/works", { title, text });
}

export async function fetchStatus(slug: string): Promise<AnalysisStatus> {
  return getJSON<AnalysisStatus>(`/api/v1/works/${encodeURIComponent(slug)}/status`);
}

// Fenced semantic search: only passages revealed by chapter n, with a cited answer.
export async function searchWork(slug: string, n: number, q: string): Promise<SearchResponse> {
  return getJSON<SearchResponse>(
    `/api/v1/works/${encodeURIComponent(slug)}/search?n=${n}&q=${encodeURIComponent(q)}`,
  );
}

// True delete of a user novel (local data only; the demo is protected server-side).
export async function deleteWork(slug: string): Promise<void> {
  const resp = await fetch(`/api/v1/works/${encodeURIComponent(slug)}`, { method: "DELETE" });
  if (!resp.ok) {
    throw new Error(await errorMessage(resp, `DELETE /works/${slug}`));
  }
}
