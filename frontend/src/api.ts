import type { GraphResponse, WorkModel } from "./types";

// Thin typed client over the fenced FastAPI routes. `n` is mandatory on every data
// route (the server returns 422 without it) — the reading position is never optional.

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`${resp.status} ${resp.statusText} for ${url}`);
  }
  return (await resp.json()) as T;
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
