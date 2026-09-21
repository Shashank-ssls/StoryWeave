import { useChapter } from "./chapter/ChapterProvider";

// The current work's title for the rail/header, read off the chapter model (which owns
// the /works lookup since R3 — it needs chapter_count before it can validate the
// bookmark, so one fetch serves both). R2's standalone fetch-and-find hook is gone.
export function useWorkTitle(): string {
  const { work, workError } = useChapter();
  if (work) return work.title;
  return workError ? "Unknown novel" : "Loading…";
}
