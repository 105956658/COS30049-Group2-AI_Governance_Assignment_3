import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // strictPort: the back end's CORS list names http://localhost:3000 exactly, so fail
    // loudly instead of silently moving to 3001 where every API call would be refused.
    strictPort: true,
    proxy: {
      // /api/* is forwarded to FastAPI on port 8000, so the browser only talks to :3000.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
