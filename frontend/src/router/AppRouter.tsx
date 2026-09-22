import { useHashRoute } from "./useHashRoute";
import TypeScale from "../dev/TypeScale";
import CodexApp from "../codex/CodexApp";

// Top-level route switch (FRONTEND_OVERHAUL.md §5 Phase 2 / R2). `#/_type` is the one
// non-reader route handled here directly; everything else is a real Codex screen, routed
// on into CodexApp (which owns the mural/vignette background layers). The old app's
// `#/_legacy` route was deleted whole at R9 step 8 (FRONTEND_OVERHAUL.md §9).
export default function AppRouter(): JSX.Element {
  const route = useHashRoute();

  if (route.name === "type-scale") return <TypeScale />;

  return <CodexApp route={route} />;
}
