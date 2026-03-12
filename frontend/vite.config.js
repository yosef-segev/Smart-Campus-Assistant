import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI backend during development
    proxy: {
      "/ask": "http://127.0.0.1:8000",
    },
  },
});
