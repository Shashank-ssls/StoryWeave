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
import type { ArcModel, ArcsResponse, GraphElements, GraphResponse, WorkModel } from "../../types";
import { diffGraphs, type GraphDiff, type Reveal } from "../../graph/diff";
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

// R6 (DESIGN_SPEC §8.2): a forward commit whose diff carries >=1 reveal hands the whole
// batch to the reveal UI (RevealChrome) instead of the plain forward toast — see
// `requestChapter`'s forward branch below. Never set on the initial load, a reload, a
// backward move or a failed fetch (those paths never reach this branch at all).
export interface PendingReveal {
  id: number;
  n: number;
  reveals: Reveal[];
}

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
  /** Fenced payload for `bookmark - 1` (F8: "changed" tags diff n against n−1), null at
   *  chapter 1 or while it loads. Always ≤ bookmark, always via the same cache. */
  prevData: GraphElements | null;
  /** D6/F6 (integration phase): named chapter-range arcs at the current bookmark,
   *  server-fenced (a not-yet-started arc's `name` is already null on arrival — the
   *  client never redacts anything itself). Empty for a work with none configured
   *  (Hollow Crown); callers fall back to blocks-of-100 in that case. */
  arcs: ArcModel[];
  /** Chapter currently being fetched, or null when idle. */
  loading: number | null;
  banner: ChapterBanner | null;
  toast: ChapterToast | null;
  dialog: { open: boolean; prefill: number };
  /** R6: set only by a forward commit whose diff has >=1 reveal (§8.2). Consumed once by
   *  RevealChrome via `dismissReveal`. */
  pendingReveal: PendingReveal | null;
  /** The only way the bookmark moves. Validates, then runs §8.1's forward/backward flow. */
  requestChapter(n: number): void;
  openDialog(prefill?: number): void;
  closeDialog(): void;
  dismissToast(): void;
  dismissBanner(): void;
  dismissReveal(): void;
  /** Read-only cache access for the Dossier's "replay this reveal" (R6 §8.2): whatever
   *  chapter payload is already in memory, never a fetch. Returns null if that chapter was
   *  never visited/prefetched this session (replay then falls back to a normal reveal —
   *  see `graph/diff.ts`'s `classifyReveal`). */
  getCachedPayload(n: number): GraphElements | null;
  /** R7 (Chronicle §6.4): fetches every chapter 1..min(upTo, bookmark) not already cached,
   *  so the identity timeline (which pair was revealed when, and whether it later deepened)
   *  can be reconstructed from `getCachedPayload` alone. F1-safe by construction — it never
   *  requests above the current bookmark, and never touches `bookmark`/`data`/`banner`; a
   *  request that fails is simply left uncached (the timeline degrades per-pair, the same
   *  honesty rule replay already uses). Never aborts, and is never aborted by, the main
   *  request. Resolves once every attempt has settled. */
  ensureHistory(upTo: number): Promise<void>;
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

// Same shape as fetchFencedGraph: private to this file, its own AbortSignal.
async function fetchFencedArcs(slug: string, n: number, signal: AbortSignal): Promise<ArcModel[]> {
  const resp = await fetch(`/api/v1/works/${encodeURIComponent(slug)}/arcs?n=${n}`, { signal });
  if (!resp.ok) throw new Error(`${resp.status} for arcs?n=${n}`);
  const body = (await resp.json()) as ArcsResponse;
  return body.arcs;
}

export function ChapterProvider({ slug, children }: { slug: string; children: ReactNode }): JSX.Element {
  const [work, setWork] = useState<WorkModel | null>(null);
  const [workError, setWorkError] = useState(false);
  const [bookmark, setBookmark] = useState(1);
  const [data, setData] = useState<GraphElements | null>(null);
  const [prevData, setPrevData] = useState<GraphElements | null>(null);
  const [arcs, setArcs] = useState<ArcModel[]>([]);
  const [loading, setLoading] = useState<number | null>(null);
  const [banner, setBanner] = useState<ChapterBanner | null>(null);
  const [toast, setToast] = useState<ChapterToast | null>(null);
  const [pendingReveal, setPendingReveal] = useState<PendingReveal | null>(null);
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
          if (n > old) {
            const diff = diffGraphs(prev, payload);
            // R6 §8.2: a diff with >=1 reveal goes to the reveal UI instead of the plain
            // toast — RevealChrome decides overlay vs. summary sheet vs. quiet toast.
            if (diff.reveals.length > 0) setPendingReveal({ id: Date.now(), n, reveals: diff.reveals });
            else showToast({ kind: "forward", id: Date.now(), n, diff });
          }
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

  // The n−1 payload for F8 diffing (R4). Requested only once `data` for the bookmark is
  // committed, always for bookmark−1 (≤ bookmark, so F1 holds), through the same cache
  // — a backward purge can never leave it stale because n−1 < any new bookmark that
  // still has a previous chapter. Its own controller: it must never abort, or be
  // aborted by, the main request (`load`), and a result is ignored if the bookmark has
  // moved on meanwhile.
  useEffect(() => {
    if (data === null || bookmark <= 1) {
      setPrevData(null);
      return;
    }
    const n = bookmark - 1;
    const cached = cache.current.get(n);
    if (cached) {
      setPrevData(cached);
      return;
    }
    setPrevData(null);
    const controller = new AbortController();
    fetchFencedGraph(slug, n, controller.signal)
      .then((payload) => {
        if (controller.signal.aborted || bookmarkRef.current !== bookmark) return;
        cache.current.set(n, payload);
        setPrevData(payload);
      })
      .catch(() => {
        /* no "changed" tags this chapter; the dossier itself is unaffected */
      });
    return () => controller.abort();
  }, [slug, bookmark, data]);

  // D6/F6: arc names/ranges at the current bookmark. Own controller, same reasoning
  // as prevData above — never aborts, or is aborted by, the main graph request. The
  // server already redacts a not-yet-started arc's name (query/fence.py), so this
  // effect just mirrors whatever it receives; a fetch failure leaves `arcs` at its
  // last-known value (harmless — callers fall back to blocks-of-100 on empty/stale).
  useEffect(() => {
    const controller = new AbortController();
    fetchFencedArcs(slug, bookmark, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setArcs(result);
      })
      .catch(() => {
        /* arcs are a display nicety, not load-bearing for the fence itself */
      });
    return () => controller.abort();
  }, [slug, bookmark]);

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
  const dismissReveal = useCallback((): void => setPendingReveal(null), []);
  const getCachedPayload = useCallback((n: number): GraphElements | null => cache.current.get(n) ?? null, []);

  const historyInFlight = useRef<Promise<void> | null>(null);
  const ensureHistory = useCallback(
    async (upTo: number): Promise<void> => {
      if (historyInFlight.current) await historyInFlight.current;
      const top = Math.min(upTo, bookmarkRef.current);
      const missing: number[] = [];
      for (let k = 1; k <= top; k++) if (!cache.current.has(k)) missing.push(k);
      if (missing.length === 0) return;
      const run = (async (): Promise<void> => {
        const controller = new AbortController();
        for (const k of missing) {
          if (k > bookmarkRef.current) break; // bookmark moved back mid-run
          try {
            const payload = await fetchFencedGraph(slug, k, controller.signal);
            if (k <= bookmarkRef.current) cache.current.set(k, payload);
          } catch {
            // best-effort: a chapter that fails to backfill just stays uncached — the
            // identity timeline degrades for that one pair, it never blocks the screen.
          }
        }
      })();
      historyInFlight.current = run;
      await run;
      historyInFlight.current = null;
    },
    [slug],
  );

  const value = useMemo<ChapterModel>(
    () => ({
      slug,
      work,
      workError,
      chapterCount,
      bookmark,
      data,
      prevData,
      arcs,
      loading,
      banner,
      toast,
      dialog,
      pendingReveal,
      requestChapter,
      openDialog,
      closeDialog,
      dismissToast,
      dismissBanner,
      dismissReveal,
      getCachedPayload,
      ensureHistory,
    }),
    [slug, work, workError, chapterCount, bookmark, data, prevData, arcs, loading, banner, toast,
      dialog, pendingReveal, requestChapter, openDialog, closeDialog, dismissToast, dismissBanner,
      dismissReveal, getCachedPayload, ensureHistory],
  );

  return <ChapterContext.Provider value={value}>{children}</ChapterContext.Provider>;
}
