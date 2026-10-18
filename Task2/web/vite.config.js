import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /chat and /ask go to the FastAPI app on port 8000
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/chat": "http://localhost:8000",
      "/ask": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
