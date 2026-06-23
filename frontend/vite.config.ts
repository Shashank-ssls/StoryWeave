import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The fence lives server-side; the frontend only ever talks to the FastAPI routes.
// In dev we proxy /api to the local uvicorn server so there is one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
