import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev requests to /api reach the local API without a CORS round trip.
    proxy: Object.fromEntries(
      ["/api", "/docs", "/redoc", "/openapi.json", "/health"].map((path) => [
        path,
        { target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000", changeOrigin: true },
      ]),
    ),
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
