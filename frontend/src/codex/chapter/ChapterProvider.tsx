import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { fetchWorks } from "../../api";
import type { GraphElements, GraphResponse, WorkModel } from "../../types";
import { diffGraphs, type GraphDiff } from "../../graph/diff";
import { readBookmark, writeBookmark } from "./bookmarkStore";

// The chapter model (FRONTEND_OVERHAUL.md §5 Phase 3; DESIGN_SPEC §5, §8.1, §9.1).
// One instance per open work, mounted in CodexApp keyed by slug so it survives tab
// switches (Dossier ↔ Stemma ↔ Chronicle share one bookmark, one cache, one in-flight
// request) and is torn down whole when the reader changes work.
//
// The UI's share of the spoiler fence lives here. The server fence (query/fence.py) is
// the real seal — this layer's job is to make sure the client never even ASKS for more
// than the confirmed bookmark, never caches it, and never renders a stale response:
//   F1  every request is for n <= the confirmed bookmark, or the n being confirmed now;
//       no prefetch of anything.
//   F5  moving back purges every cached chapter > new bookmark, synchronously, before
//       anything else happens.
//   §8.1 one request in flight; a new confirm aborts the previous (AbortController) AND
//       invalidates it by request token — a fetch that already resolved past the abort
//       check can still never reach state, because its token is stale by then.
//   §6.7 a failed fetch keeps the previous chapter's data and does NOT move the bookmark.

export type ChapterToast =
  | { kind: "forward"; id: number; n: number; diff: GraphDiff }
  | { kind: "backward"; id: number; n: number };

export interface ChapterBanner {
  /** Chapter that failed to load. */
  failed: number;
  /** Chapter whose data is still on screen (null when nothing is loaded yet). */
  showing: number | null;
}

export interface ChapterModel {
  slug: string;
  /** null until /works has answered. */
  work: WorkModel | null;
  workError: boolean;
  chapterCount: number;
  /** The confirmed bookmark. Only ever changes on a successful load (forward) or
   *  immediately (backward) — never speculatively. */
  bookmark: number;
  /** Fenced payload for `bookmark`, or null while the first load is pending. */
  data: GraphElements | null;
  /** Chapter currently being fetched, or null when idle. */
  loading: number | null;
  banner: ChapterBanner | null;
  toast: ChapterToast | null;
  dialog: { open: boolean; prefill: number };
  /** The only way the bookmark moves. Validates, then runs §8.1's forward/backward flow. */
  requestChapter(n: number): void;
  openDialog(prefill?: number): void;
  closeDialog(): void;
  dismissToast(): void;
  dismissBanner(): void;
}

const ChapterContext = createContext<ChapterModel | null>(null);

export function useChapter(): ChapterModel {
  const ctx = useContext(ChapterContext);
  if (!ctx) throw new Error("useChapter must be used inside <ChapterProvider>");
  return ctx;
}

const TOAST_MS = 4000;

// Raw fetch for the fenced graph route (same URL as api.ts's fetchGraph — R0 recon:
// `/api/v1/works/{slug}/graph?n={n}`) but with an AbortSignal, which api.ts's helper
// doesn't take. Kept private to this file: nothing else in the Codex UI may fetch a graph.
async function fetchFencedGraph(slug: string, n: number, signal: AbortSignal): Promise<GraphElements> {
  const resp = await fetch(`/api/v1/works/${encodeURIComponent(slug)}/graph?n=${n}`, { signal });
  if (!resp.ok) throw new Error(`${resp.status} for graph?n=${n}`);
  const body = (await resp.json()) as GraphResponse;
  return body.elements;
}

export function ChapterProvider({ slug, children }: { slug: string; children: ReactNode }): JSX.Element {
  const [work, setWork] = useState<WorkModel | null>(null);
  const [workError, setWorkError] = useState(false);
  const [bookmark, setBookmark] = useState(1);
  const [data, setData] = useState<GraphElements | null>(null);
  const [loading, setLoading] = useState<number | null>(null);
  const [banner, setBanner] = useState<ChapterBanner | null>(null);
  const [toast, setToast] = useState<ChapterToast | null>(null);
  const [dialog, setDialog] = useState({ open: false, prefill: 1 });

  // Mutable plumbing, deliberately outside React state so the fence checks are
  // synchronous and can't lag a render behind the user's action.
  const cache = useRef(new Map<number, GraphElements>());
  const abortRef = useRef<AbortController | null>(null);
  const tokenRef = useRef(0);
  const bookmarkRef = useRef(1); // mirrors `bookmark` for use inside async callbacks
  const dataRef = useRef<GraphElements | null>(null);
  const toastTimer = useRef<number | null>(null);

  const chapterCount = work?.chapter_count ?? 0;

  const invalidateInFlight = useCallback((): void => {
    tokenRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const showToast = useCallback((t: ChapterToast): void => {
    if (toastTimer.current !== null) window.clearTimeout(toastTimer.current);
    setToast(t);
    toastTimer.current = window.setTimeout(() => setToast(null), TOAST_MS);
  }, []);

  const commit = useCallback(
    (n: number, payload: GraphElements): void => {
      bookmarkRef.current = n;
      dataRef.current = payload;
      setBookmark(n);
      setData(payload);
      writeBookmark(slug, n);
    },
    [slug],
  );

  // Fetch chapter `n` (already validated as <= the bookmark being confirmed). Resolves
  // with the payload only if this request is still the live one when it lands.
  const load = useCallback(
    async (n: number): Promise<GraphElements | null> => {
      invalidateInFlight();
      const token = tokenRef.current;
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(n);
      try {
        const payload = await fetchFencedGraph(slug, n, controller.signal);
        // Token guard: an aborted request usually throws, but a response that resolved
        // in the same tick as a newer confirm would otherwise slip through — the token
        // check closes that gap regardless of what the signal did.
        if (token !== tokenRef.current) return null;
        cache.current.set(n, payload);
        return payload;
      } catch (err) {
        if (token !== tokenRef.current) return null; // superseded — not an error to show
        if ((err as { name?: string }).name === "AbortError") return null;
        throw err;
      } finally {
        if (token === tokenRef.current) {
          abortRef.current = null;
          setLoading(null);
        }
      }
    },
    [slug, invalidateInFlight],
  );

  const requestChapter = useCallback(
    (raw: number): void => {
      if (chapterCount < 1) return;
      const n = Math.trunc(raw);
      if (!Number.isInteger(n) || n < 1 || n > chapterCount) return;
      const old = bookmarkRef.current;
      if (n === old && dataRef.current !== null && loading === null) return;
      setBanner(null);

      if (n < old) {
        // Backward (§8.1): commit at once — moving back can never expose anything — and
        // purge synchronously (F5) before any await, so no cached chapter above the new
        // bookmark survives even for one tick.
        invalidateInFlight();
        for (const k of [...cache.current.keys()]) if (k > n) cache.current.delete(k);
        const cached = cache.current.get(n) ?? null;
        bookmarkRef.current = n;
        dataRef.current = cached;
        setBookmark(n);
        setData(cached);
        writeBookmark(slug, n);
        showToast({ kind: "backward", id: Date.now(), n });
        if (cached) return;
        void load(n)
          .then((payload) => {
            if (payload && bookmarkRef.current === n) {
              dataRef.current = payload;
              setData(payload);
            }
          })
          .catch(() => setBanner({ failed: n, showing: null }));
        return;
      }

      // Forward, or the initial load / a retry of the current chapter. Old data stays on
      // screen under the loading wash; the bookmark moves only once the payload is here.
      const prev = cache.current.get(old) ?? null;
      void load(n)
        .then((payload) => {
          if (!payload) return;
          commit(n, payload);
          if (n > old) showToast({ kind: "forward", id: Date.now(), n, diff: diffGraphs(prev, payload) });
        })
        .catch(() => setBanner({ failed: n, showing: dataRef.current ? bookmarkRef.current : null }));
    },
    [chapterCount, slug, loading, invalidateInFlight, load, commit, showToast],
  );

  // Resolve the work (title + chapter_count) once per slug. Nothing about the graph is
  // requested until chapter_count is known, because the stored bookmark can't be
  // validated without it.
  useEffect(() => {
    let live = true;
    setWork(null);
    setWorkError(false);
    fetchWorks()
      .then((works) => {
        if (!live) return;
        const found = works.find((w) => w.slug === slug) ?? null;
        setWork(found);
        if (!found) setWorkError(true);
      })
      .catch(() => {
        if (live) setWorkError(true);
      });
    return () => {
      live = false;
    };
  }, [slug]);

  // Initial load: validated stored bookmark (default 1), fetched exactly once. Runs after
  // the work resolves; re-runs only if the slug changes (the provider is keyed by slug,
  // so in practice that means a fresh instance with an empty cache).
  const initialised = useRef(false);
  useEffect(() => {
    if (!work || initialised.current) return;
    initialised.current = true;
    const start = readBookmark(slug, work.chapter_count);
    bookmarkRef.current = start;
    setBookmark(start);
    writeBookmark(slug, start); // normalises a tampered value on disk too
    void load(start)
      .then((payload) => {
        if (payload) commit(start, payload);
      })
      .catch(() => setBanner({ failed: start, showing: null }));
  }, [work, slug, load, commit]);

  // Unmount (work change / leaving the work): nothing in flight may outlive the model.
  useEffect(
    () => () => {
      invalidateInFlight();
      cache.current.clear();
      if (toastTimer.current !== null) window.clearTimeout(toastTimer.current);
    },
    [invalidateInFlight],
  );

  const openDialog = useCallback(
    (prefill?: number): void => {
      if (chapterCount < 1) return; // no book length yet → nothing can be validated, so no dialog
      const p = prefill ?? bookmarkRef.current;
      setDialog({ open: true, prefill: Math.min(Math.max(1, p), chapterCount) });
    },
    [chapterCount],
  );
  const closeDialog = useCallback((): void => setDialog((d) => ({ ...d, open: false })), []);
  const dismissToast = useCallback((): void => setToast(null), []);
  const dismissBanner = useCallback((): void => setBanner(null), []);

  const value = useMemo<ChapterModel>(
    () => ({
      slug,
      work,
      workError,
      chapterCount,
      bookmark,
      data,
      loading,
      banner,
      toast,
      dialog,
      requestChapter,
      openDialog,
      closeDialog,
      dismissToast,
      dismissBanner,
    }),
    [slug, work, workError, chapterCount, bookmark, data, loading, banner, toast, dialog,
      requestChapter, openDialog, closeDialog, dismissToast, dismissBanner],
  );

  return <ChapterContext.Provider value={value}>{children}</ChapterContext.Provider>;
}
