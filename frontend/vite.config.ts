import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The fence lives server-side; the frontend only ever talks to the FastAPI routes.
// In dev we proxy /api to the local uvicorn server so there is one origin.
//
// `STORYWEAVE_API_TARGET` is a verification-only knob. Capturing a DIFFERENT corpus (the
// retrofit's Ninth House DB, for the ch40 Rule Zero screenshots) means pointing at a
// second uvicorn on another port instead of stopping the one serving the demo — and the
// capture has to run against the DEV build, because `cyRegistry` only exposes
// `window.__storyweaveCy` (the drawn ids, the label boxes) when `import.meta.env.DEV`.
// It changes nothing about a production build: the shipped app is same-origin.
// Read off `globalThis` rather than a bare `process`, so this stays typed without adding
// `@types/node` to the frontend for one string.
const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env;
const apiTarget = env?.STORYWEAVE_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
