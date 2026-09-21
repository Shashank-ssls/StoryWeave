import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// The Codex theme's tokens + fonts (bundled offline via @fontsource, no runtime font CDN —
// see tokens.css). Imported once, globally — this is the only stylesheet every route
// shares. The old app's stylesheet is loaded lazily by LegacyRoute, only for `#/_legacy`,
// so it can never bleed onto the new Codex screens (see the R1 report's `.swatch`
// collision, and FRONTEND_OVERHAUL.md §9 R2's "CSS collision rule").
import "./styles/tokens.css";
import AppRouter from "./router/AppRouter";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root");

createRoot(root).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>,
);
