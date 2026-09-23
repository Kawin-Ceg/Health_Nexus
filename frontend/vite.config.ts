import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Same-origin in development: the httpOnly refresh cookie (path /api/v1/auth)
    // then needs no CORS or credentials gymnastics.
    proxy: { "/api": { target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000", changeOrigin: false } },
  },
});
