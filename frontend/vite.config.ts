import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Docker maps API to host 8787 (see docker-compose.yml); local uvicorn can use 8000.
const backend = { target: 'http://127.0.0.1:8787', changeOrigin: true }

// https://vite.dev/config/
// Do NOT proxy bare `/form` or `/admin` — those are React Router paths.
// List specific API prefixes; longer paths first where it matters.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/form/questions/reorder': backend,
      '/form/questions': backend,
      '/form/flow': backend,
      '/form/structure': backend,
      '/form/pages': backend,
      '/auth': backend,
      '/responses': backend,
      '/admin/form-access': backend,
      '/admin/admin-access': backend,
      '/admin/audit-events': backend,
      '/health': backend,
    },
  },
})
