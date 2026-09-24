import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev-time proxy so the frontend can call relative /api/* paths against
// the backend at localhost:8000 without CORS configuration during local
// development. In production this would be replaced by a real reverse
// proxy or the frontend build being served from the same origin as the
// API -- see README for how docker-compose wires this in Phase 14.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
