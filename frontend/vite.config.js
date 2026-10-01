import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    watch: {
      usePolling: process.env.VITE_USE_POLLING === "true",
      interval: 300,
    },
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
