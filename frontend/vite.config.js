import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During local dev, proxy /api calls to the FastAPI backend so there are no
// CORS issues and the frontend can call relative URLs (same as in production
// when served behind a single origin / reverse proxy).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
