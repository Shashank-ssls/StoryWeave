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
import type {
  ArcModel,
  ArcsResponse,
  CastSize,
  GraphElements,
  GraphResponse,
  WorkModel,
} from "../../types";
import { diffGraphs, type GraphDiff, type Reveal } from "../../graph/diff";
import { readBookmark, writeBookmark } from "./bookmarkStore";

// The chapter model (FRONTEND_OVERHAUL.md §5 Phase 3; DESIGN_SPEC §5, §8.1, §9.1).
// One instance per open work, mounted in CodexApp keyed by slug so it survives tab
// switches (Dossier ↔ Stemma share one bookmark, one cache, one in-flight
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

/**
 * R7: what the reader has asked to SEE, as opposed to how far they have read.
 *
 * These are display choices and they live on the server (retrofit rules 1 and 6): every
 * change re-requests `/graph`, and nothing is ever filtered out of a payload here. v1's
 * equivalents were client-side array filters over a payload that always contained the
 * whole book's cast — defect D3, and the reason the dial appeared to do nothing.
 *
 * `types` always contains "Character" (rule 2: the default graph is people), plus
 * whichever overlays are toggled on. `cast` is the dial.
 */
export interface ViewParams {
  cast: CastSize;
  groups: boolean;
  places: boolean;
  items: boolean;
}

/** The Stemma's default: people only, main cast of twenty (retrofit rule 2). */
export const DEFAULT_VIEW: ViewParams = {
  cast: "20",
  groups: false,
  places: false,
  items: false,
};

/**
 * The Dossier's view: everything the fence allows.
 *
 * The Dossier is not a picture of the cast, it is a page ABOUT one entity, reached by a
 * URL that may name anyone the reader has met. Serving it the Stemma's top-twenty would
 * make it answer "not present" for a revealed character — a false statement about the
 * fence, and a worse bug than the one the dial fixes. Each screen therefore declares the
 * view it needs on mount; the request still goes to the server either way.
 */
export const FULL_VIEW: ViewParams = {
  cast: "all",
  groups: true,
  places: true,
  items: true,
};

export function sameView(a: ViewParams, b: ViewParams): boolean {
  return a.cast === b.cast && a.groups === b.groups && a.places === b.places && a.items === b.items;
}

/** The `types` query parameter for a set of overlay toggles. */
export function typesParam(v: ViewParams): string {
  const out = ["Character"];
  if (v.groups) out.push("Organization");
  if (v.places) out.push("Place");
  if (v.items) out.push("Item");
  return out.join(",");
}

/** Cache key: a payload is only reusable for the same chapter AND the same view. */
function cacheKey(n: number, v: ViewParams): string {
  return `${n}|${v.cast}|${typesParam(v)}`;
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
  /** R7: what the reader asked to SEE (cast dial + overlay toggles). Server-side. */
  view: ViewParams;
  /** The only way the bookmark moves. Validates, then runs §8.1's forward/backward flow. */
  requestChapter(n: number): void;
  /** R7: the only way the view changes. Re-requests /graph; never filters locally. */
  setView(next: ViewParams): void;
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
async function fetchFencedGraph(
  slug: string,
  n: number,
  view: ViewParams,
  signal: AbortSignal,
): Promise<GraphElements> {
  const query = `n=${n}&cast=${view.cast}&types=${encodeURIComponent(typesParam(view))}`;
  const resp = await fetch(`/api/v1/works/${encodeURIComponent(slug)}/graph?${query}`, { signal });
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

export function ChapterProvider({
  slug,
  initialView = DEFAULT_VIEW,
  children,
}: {
  slug: string;
  /** The view the FIRST load should request. Passed by the route (see CodexApp), because
   *  a screen that declares its view after mounting would cost a second `/graph` request
   *  on every first visit — which the fence specs count, and rightly. */
  initialView?: ViewParams;
  children: ReactNode;
}): JSX.Element {
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
  const [view, setViewState] = useState<ViewParams>(initialView);

  // Mutable plumbing, deliberately outside React state so the fence checks are
  // synchronous and can't lag a render behind the user's action.
  const cache = useRef(new Map<string, GraphElements>());
  const abortRef = useRef<AbortController | null>(null);
  const tokenRef = useRef(0);
  const bookmarkRef = useRef(1); // mirrors `bookmark` for use inside async callbacks
  const dataRef = useRef<GraphElements | null>(null);
  const toastTimer = useRef<number | null>(null);
  const viewRef = useRef<ViewParams>(initialView); // mirrors `view` for async callbacks
  const inFlight = useRef<{ n: number; view: ViewParams } | null>(null);
  /** A view change that arrived while a chapter move was in flight; applied afterwards. */
  const pendingView = useRef(false);

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
      // Synchronous mirror of what is being fetched. `loading` state lags a render, and
      // `setView` has to know about an in-flight request in the same tick to stay
      // idempotent — see the request-count bug fixed there.
      inFlight.current = { n, view: viewRef.current };
      setLoading(n);
      try {
        const payload = await fetchFencedGraph(slug, n, viewRef.current, controller.signal);
        // Token guard: an aborted request usually throws, but a response that resolved
        // in the same tick as a newer confirm would otherwise slip through — the token
        // check closes that gap regardless of what the signal did.
        if (token !== tokenRef.current) return null;
        cache.current.set(cacheKey(n, viewRef.current), payload);
        return payload;
      } catch (err) {
        if (token !== tokenRef.current) return null; // superseded — not an error to show
        if ((err as { name?: string }).name === "AbortError") return null;
        throw err;
      } finally {
        if (token === tokenRef.current) {
          abortRef.current = null;
          inFlight.current = null;
          setLoading(null);
        }
      }
    },
    [slug, invalidateInFlight],
  );

  /** Apply a view change that had to wait for a chapter move to land. No-op otherwise. */
  const applyPendingView = useCallback((): void => {
    if (!pendingView.current) return;
    pendingView.current = false;
    const n = bookmarkRef.current;
    const cached = cache.current.get(cacheKey(n, viewRef.current));
    if (cached) {
      dataRef.current = cached;
      setData(cached);
      return;
    }
    void load(n)
      .then((payload) => {
        if (payload && bookmarkRef.current === n) {
          dataRef.current = payload;
          setData(payload);
        }
      })
      .catch(() => {
        /* the chapter itself is already committed; a failed view refetch keeps what is
           on screen rather than blanking it (§6.7's rule, applied to the view). */
      });
  }, [load]);

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
        for (const k of [...cache.current.keys()]) if (Number(k.split("|")[0]) > n) cache.current.delete(k);
        const cached = cache.current.get(cacheKey(n, viewRef.current)) ?? null;
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
            applyPendingView();
          })
          .catch(() => setBanner({ failed: n, showing: null }));
        return;
      }

      // Forward, or the initial load / a retry of the current chapter. Old data stays on
      // screen under the loading wash; the bookmark moves only once the payload is here.
      const prev = cache.current.get(cacheKey(old, viewRef.current)) ?? null;
      void load(n)
        .then((payload) => {
          if (!payload) return;
          commit(n, payload);
          applyPendingView(); // a tab/view switch that waited for this move
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
    [chapterCount, slug, loading, invalidateInFlight, load, commit, showToast, applyPendingView],
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
    const cached = cache.current.get(cacheKey(n, viewRef.current));
    if (cached) {
      setPrevData(cached);
      return;
    }
    setPrevData(null);
    const controller = new AbortController();
    fetchFencedGraph(slug, n, viewRef.current, controller.signal)
      .then((payload) => {
        if (controller.signal.aborted || bookmarkRef.current !== bookmark) return;
        cache.current.set(cacheKey(n, viewRef.current), payload);
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

  // R7: the only way the view changes. It goes back to the SERVER — retrofit rule 6, no
  // client-side filtering of any kind — so the payload the canvas draws is always exactly
  // what the API decided to serve for this chapter and these settings. The bookmark is
  // untouched: changing what you look at is not reading further, so no toast, no reveal,
  // no diff, and F1 is unaffected (the request is still for the confirmed bookmark).
  const setView = useCallback(
    (next: ViewParams): void => {
      // Idempotent: a screen re-declaring the view it already has must not re-fetch.
      //
      // "Already has" includes "is fetching right now". The first version only checked
      // `dataRef.current !== null`, so on a first visit — where the mount effect runs
      // while the provider's own initial load is still in flight — the same view was
      // re-requested, and a re-render did it again: [MEASURED] THREE identical
      // `/graph?n=1&cast=all&types=…` requests on one page load, caught by
      // `fence.spec.ts` F1 ("first visit … requests only n=1"). The fence specs count
      // requests exactly, and here they were counting a real bug.
      const settled = dataRef.current !== null;
      const fetching = inFlight.current !== null && sameView(inFlight.current.view, next);
      if (sameView(next, viewRef.current) && (settled || fetching)) return;
      viewRef.current = next;
      // React runs a CHILD's effects before its parent's, so a screen declaring its view
      // on mount gets here before this provider's own initial load has even started.
      // Recording the view and returning lets that one load request the right thing,
      // instead of racing it with a second identical request (the other half of the
      // three-requests-on-first-visit bug above).
      if (!initialised.current) {
        setViewState(next);
        return;
      }
      // A chapter move already in flight OWNS the request. Changing the view must never
      // cancel it: the reader's chapter is the primary action and the view is secondary,
      // and `load` aborts whatever is in flight. Without this, switching tabs during a
      // forward fetch silently lost the move — the bookmark stayed where it was
      // (`fence.spec.ts` "tab switch during a forward fetch: bookmark still commits").
      // The view is recorded and re-requested once the move lands.
      if (inFlight.current !== null) {
        setViewState(next);
        pendingView.current = true;
        return;
      }
      setViewState(next);
      const n = bookmarkRef.current;
      const cached = cache.current.get(cacheKey(n, next));
      if (cached) {
        dataRef.current = cached;
        setData(cached);
        return;
      }
      void load(n)
        .then((payload) => {
          if (payload && bookmarkRef.current === n) {
            dataRef.current = payload;
            setData(payload);
          }
        })
        .catch(() => setBanner({ failed: n, showing: dataRef.current ? n : null }));
    },
    [load],
  );
  const getCachedPayload = useCallback(
    (n: number): GraphElements | null => cache.current.get(cacheKey(n, viewRef.current)) ?? null,
    [],
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
      view,
      requestChapter,
      setView,
      openDialog,
      closeDialog,
      dismissToast,
      dismissBanner,
      dismissReveal,
      getCachedPayload,
    }),
    [slug, work, workError, chapterCount, bookmark, data, prevData, arcs, loading, banner, toast,
      dialog, pendingReveal, view, requestChapter, setView, openDialog, closeDialog, dismissToast,
      dismissBanner, dismissReveal, getCachedPayload],
  );

  return <ChapterContext.Provider value={value}>{children}</ChapterContext.Provider>;
}
