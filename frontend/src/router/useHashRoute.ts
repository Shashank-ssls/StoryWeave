import { useEffect, useState } from "react";

// Hand-rolled hash router (FRONTEND_OVERHAUL.md §6 Phase 2 / R2; DESIGN_SPEC.md §5).
// Routes: landing `#/`, `#/add` (R9 step 8: the ingest form, ported off the deleted
// legacy app), `#/work/:slug/entity/:id`, `#/work/:slug/web?focus=:id`,
// `#/work/:slug/chronicle`, plus the dev-only `#/_type` (token gallery). The chapter
// bookmark MUST NOT appear in any URL (DESIGN_SPEC §5) — nothing here ever reads or
// writes a chapter number.

export type Route =
  | { name: "landing" }
  | { name: "add" }
  | { name: "work-entity"; slug: string; entityId: string }
  | { name: "work-web"; slug: string; focus: string | null }
  | { name: "work-chronicle"; slug: string }
  | { name: "type-scale" };

export type WorkRoute = Extract<
  Route,
  { name: "work-entity" } | { name: "work-web" } | { name: "work-chronicle" }
>;
export type CodexRoute = Extract<Route, { name: "landing" } | { name: "add" }> | WorkRoute;

// The entity-id placeholder used when `#/work/:slug` is visited with no entity chosen yet.
// R4 replaces this redirect target with the real highest-degree person.
export const PENDING_ENTITY = "_pending";

function parse(hash: string): Route {
  const raw = hash.replace(/^#/, "");
  const [pathPart, queryPart] = raw.split("?");
  const segs = (pathPart ?? "").split("/").filter(Boolean);

  if (segs.length === 0) return { name: "landing" };
  if (segs[0] === "_type") return { name: "type-scale" };
  if (segs[0] === "add") return { name: "add" };

  if (segs[0] === "work" && segs[1]) {
    const slug = decodeURIComponent(segs[1]);
    if (segs[2] === "entity" && segs[3]) {
      return { name: "work-entity", slug, entityId: decodeURIComponent(segs[3]) };
    }
    if (segs[2] === "web") {
      const params = new URLSearchParams(queryPart ?? "");
      return { name: "work-web", slug, focus: params.get("focus") };
    }
    if (segs[2] === "chronicle") {
      return { name: "work-chronicle", slug };
    }
    // `#/work/:slug` with no entity chosen — resolves to the pending-entity placeholder.
    return { name: "work-entity", slug, entityId: PENDING_ENTITY };
  }

  // Unknown route → landing (never a 404 screen; not in scope this phase).
  return { name: "landing" };
}

export function routePath(route: Route): string {
  switch (route.name) {
    case "landing":
      return "#/";
    case "add":
      return "#/add";
    case "type-scale":
      return "#/_type";
    case "work-entity":
      return `#/work/${encodeURIComponent(route.slug)}/entity/${encodeURIComponent(route.entityId)}`;
    case "work-web":
      return `#/work/${encodeURIComponent(route.slug)}/web${
        route.focus ? `?focus=${encodeURIComponent(route.focus)}` : ""
      }`;
    case "work-chronicle":
      return `#/work/${encodeURIComponent(route.slug)}/chronicle`;
  }
}

export function navigate(route: Route): void {
  window.location.hash = routePath(route);
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash));

  useEffect(() => {
    const onHashChange = (): void => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // `#/work/:slug` (no entity) already resolves to the pending-entity route for
  // rendering, but the visible URL should reflect where the reader actually landed
  // (DESIGN_SPEC §5: URLs are shareable) — normalise it via replaceState so this doesn't
  // add a spurious history entry or re-fire hashchange.
  useEffect(() => {
    if (route.name === "work-entity" && route.entityId === PENDING_ENTITY) {
      const wanted = routePath(route);
      if (window.location.hash !== wanted) {
        window.history.replaceState(null, "", wanted);
      }
    }
  }, [route]);

  return route;
}
