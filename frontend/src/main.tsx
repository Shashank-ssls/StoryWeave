import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// The Codex theme's tokens + fonts (bundled offline via @fontsource, no runtime font CDN —
// see tokens.css). Imported once, globally — this is the only stylesheet every route
// shares. (The old app's own stylesheet, once loaded lazily only for `#/_legacy`, was
// deleted whole with the legacy route at R9 step 8 — see FRONTEND_OVERHAUL.md §9.)
import "./styles/tokens.css";
import AppRouter from "./router/AppRouter";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root");

createRoot(root).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>,
);
