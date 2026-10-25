/**
 * Vite Configuration (frontend/vite.config.ts)
 * =====================================================================
 * WHAT THIS FILE DOES:
 * Configures Vite to bundle our React + TypeScript frontend and sets up a local development proxy
 * so any request to `/api/*` from `http://localhost:5173` is automatically forwarded to our FastAPI
 * server running on `http://127.0.0.1:8000`.
 *
 * WHY WE WROTE IT THIS WAY:
 * By using relative `/api/v1/...` URLs in our React code with a Vite proxy in local development,
 * the exact same frontend code works both locally (`localhost:5173` -> `127.0.0.1:8000`) AND in
 * production on Vercel (`https://your-app.vercel.app/api/v1/...`) without changing any URLs!
 * =====================================================================
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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