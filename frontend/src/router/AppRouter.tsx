import { useHashRoute } from "./useHashRoute";
import LegacyRoute from "../codex/LegacyRoute";
import TypeScale from "../dev/TypeScale";
import CodexApp from "../codex/CodexApp";

// Top-level route switch (FRONTEND_OVERHAUL.md §5 Phase 2 / R2). `#/_legacy` and
// `#/_type` are non-reader routes handled here directly; everything else is a real Codex
// screen, routed on into CodexApp (which owns the mural/vignette background layers).
export default function AppRouter(): JSX.Element {
  const route = useHashRoute();

  if (route.name === "legacy") return <LegacyRoute />;
  if (route.name === "type-scale") return <TypeScale />;

  return <CodexApp route={route} />;
}
