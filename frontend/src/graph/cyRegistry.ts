// Dev-only bookkeeping for Cytoscape instances and running layouts (R5 lifecycle rule:
// the infinite cola layout and the cy instance must die on unmount / tab switch / work
// switch). Exposed on `window.__storyweaveCy` in dev builds only so the Playwright
// lifecycle test can assert nothing is orphaned. Never rendered in the UI.

export const cyRegistry = {
  instances: 0,
  layouts: 0,
  /** Total instances ever created — lets a test prove churn actually happened. */
  created: 0,
  /** The live Stemma instance (dev only) so tests can read drawn ids and label boxes. */
  stemma: null as unknown,
};

declare global {
  interface Window {
    __storyweaveCy?: typeof cyRegistry;
  }
}

if (import.meta.env.DEV && typeof window !== "undefined") {
  window.__storyweaveCy = cyRegistry;
}
