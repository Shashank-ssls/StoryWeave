import { navigate, PENDING_ENTITY, type WorkRoute } from "../router/useHashRoute";
import { codexTheme } from "./theme";
import type { TabItem } from "../components/Tabs/Tabs";

// Shared by Dossier/Stemma/Chronicle — DESIGN_SPEC.md §5's three tabs, in one place so
// their keys/labels/navigation can't drift between the three screens that render them.
export const tabItems: TabItem[] = [
  { key: "entity", label: codexTheme.dossierTab },
  { key: "web", label: codexTheme.web },
  { key: "chronicle", label: codexTheme.chronicleTab },
];

export function tabKeyForRoute(route: WorkRoute): string {
  return route.name === "work-entity" ? "entity" : route.name === "work-web" ? "web" : "chronicle";
}

/** Navigates to `key`'s screen, keeping the current entity id if the Dossier is already focused on one. */
export function navigateToTab(key: string, route: WorkRoute): void {
  const { slug } = route;
  if (key === "entity") {
    const entityId = route.name === "work-entity" ? route.entityId : PENDING_ENTITY;
    navigate({ name: "work-entity", slug, entityId });
  } else if (key === "web") {
    navigate({ name: "work-web", slug, focus: null });
  } else if (key === "chronicle") {
    navigate({ name: "work-chronicle", slug });
  }
}
