import { useEffect, useState } from "react";
import App from "../App";

// `#/_legacy` — the entire old "constellation" app, unchanged (FRONTEND_OVERHAUL.md §9 R2:
// deleted in R9, once every screen it covers has a Codex replacement). Its stylesheet is
// loaded lazily, only when this route actually mounts, rather than globally in main.tsx —
// the R1 lesson was that a global, unscoped legacy stylesheet can silently clobber new
// class names (it did, once — see the R1 report). Loading it on demand means the new
// Codex screens never share a document with it at all.
export default function LegacyRoute(): JSX.Element | null {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let live = true;
    void import("../styles.css").then(() => {
      if (live) setReady(true);
    });
    return () => {
      live = false;
    };
  }, []);

  if (!ready) return null;
  return <App />;
}
