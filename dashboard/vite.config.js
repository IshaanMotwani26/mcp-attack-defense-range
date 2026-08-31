import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, the dashboard runs on :5173 and the FastAPI backend on :8000.
// Proxy REST (/api) and the scan socket (/ws) so the browser only ever
// talks to one origin — no CORS juggling, and the WebSocket upgrade works.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
