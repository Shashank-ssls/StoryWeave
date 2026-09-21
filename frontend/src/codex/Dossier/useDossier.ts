import { useMemo } from "react";
import { useChapter } from "../chapter/ChapterProvider";
import { diffGraphs } from "../../graph/diff";
import { buildViewModel, principalOf, type ViewModel, type VmNode } from "../../graph/viewModel";

// Everything the Dossier screen derives from the chapter model, memoised on the fenced
// payloads. `changed` (F8) uses ONLY graph(n) and graph(n−1) — both fenced, both from the
// R3 cache — and is empty at chapter 1 (there is no n−1 to diff against; tagging the
// whole cast "changed" on the first page would say nothing).

export interface DossierData {
  vm: ViewModel | null;
  principal: VmNode | null;
  /** Entity ids that are new at the bookmark chapter, or gained an identity edge revealed exactly there. */
  changed: Set<string>;
}

export function useDossier(): DossierData {
  const { data, prevData, bookmark } = useChapter();

  const vm = useMemo(() => (data ? buildViewModel(data) : null), [data]);

  const changed = useMemo(() => {
    const out = new Set<string>();
    if (!data || !prevData || bookmark <= 1) return out;
    const d = diffGraphs(prevData, data);
    for (const n of d.newNodes) out.add(n.id);
    for (const e of d.newIdentityEdges) {
      if (e.revealed_chapter === bookmark) {
        out.add(e.source);
        out.add(e.target);
      }
    }
    return out;
  }, [data, prevData, bookmark]);

  return { vm, principal: vm ? principalOf(vm) : null, changed };
}
