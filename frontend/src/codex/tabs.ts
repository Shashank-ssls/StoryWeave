import { navigate, PENDING_ENTITY, type WorkRoute } from "../router/useHashRoute";
import { codexTheme } from "./theme";
import type { TabItem } from "../components/Tabs/Tabs";

// Shared by the Dossier and the Stemma, in one place so their keys/labels/navigation
// can't drift between the two screens that render them. R7 removed the third tab
// (Chronicle/timeline) along with its route and code.
export const tabItems: TabItem[] = [
  { key: "entity", label: codexTheme.dossierTab },
  { key: "web", label: codexTheme.web },
];

export function tabKeyForRoute(route: WorkRoute): string {
  return route.name === "work-entity" ? "entity" : "web";
}

/** Navigates to `key`'s screen, keeping the current entity id if the Dossier is already focused on one. */
export function navigateToTab(key: string, route: WorkRoute): void {
  const { slug } = route;
  if (key === "entity") {
    const entityId = route.name === "work-entity" ? route.entityId : PENDING_ENTITY;
    navigate({ name: "work-entity", slug, entityId });
  } else if (key === "web") {
    navigate({ name: "work-web", slug, focus: null });
  }
}
