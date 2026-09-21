import { useEffect, useState } from "react";
import { fetchWorks } from "../api";

// The first real data on screen in the Codex UI (FRONTEND_OVERHAUL.md §5 Phase 2 / R2
// point 7): reads the real `/works` list and resolves the current work's title. Shared by
// Dossier/Stemma/Chronicle so the fetch-and-find logic isn't tripled. Nothing else in R2
// fetches data — everything else on these screens is a placeholder box.
export function useWorkTitle(slug: string): string {
  const [title, setTitle] = useState("Loading…");

  useEffect(() => {
    let live = true;
    setTitle("Loading…");
    fetchWorks()
      .then((works) => {
        if (!live) return;
        const work = works.find((w) => w.slug === slug);
        setTitle(work ? work.title : "Unknown novel");
      })
      .catch(() => {
        if (live) setTitle("Unknown novel");
      });
    return () => {
      live = false;
    };
  }, [slug]);

  return title;
}
