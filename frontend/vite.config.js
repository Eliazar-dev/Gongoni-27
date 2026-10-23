import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In production Django serves the built files under /static/, so assets are built with that prefix.
// In development (npm run dev) the API is proxied to Django on port 8000.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/' : '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: { outDir: 'dist', emptyOutDir: true },
}))
