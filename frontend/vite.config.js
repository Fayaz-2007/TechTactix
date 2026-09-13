import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The app itself only ever calls relative paths (e.g. fetch("/api/chat")),
// so the production build works unmodified whether the backend is on the
// same machine or reached over the LAN. This proxy exists purely so
// `npm run dev` is pleasant locally (it has no effect on `npm run build`).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
