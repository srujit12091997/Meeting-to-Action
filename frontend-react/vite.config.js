import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built app is served by FastAPI under /app/. In dev, Vite proxies /api to the backend.
export default defineConfig({
  plugins: [react()],
  base: '/app/',
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
