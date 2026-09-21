import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// The Codex theme's tokens + fonts (bundled offline via @fontsource, no runtime font CDN —
// see tokens.css). Imported once, globally, ahead of the old app's own stylesheet.
import "./styles/tokens.css";
import App from "./App";
import "./styles.css";
import TypeScale from "./dev/TypeScale";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root");

// Hidden dev route for the redesign's token/primitive inventory (FRONTEND_OVERHAUL.md
// Phase 1 / R1). Deliberately the smallest possible check — R2 replaces this with the
// real hash router and this branch goes away.
const isTypeRoute = window.location.hash === "#/_type";

createRoot(root).render(
  <StrictMode>{isTypeRoute ? <TypeScale /> : <App />}</StrictMode>,
);
