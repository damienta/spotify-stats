import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// The deployed API (infra/live output `api_url`). Override with API_URL in web/.env.local.
const DEFAULT_API = 'https://5o2g53vz3bhz4cgroqkvquvosm0dorcs.lambda-url.eu-north-1.on.aws'

export default defineConfig(({ mode }) => {
  const api = loadEnv(mode, process.cwd(), '').API_URL || DEFAULT_API
  // The browser calls /api on this dev server, which forwards to the API. Same origin, so the
  // API needs no CORS setup while the app only runs locally.
  const proxy = {
    '/api': { target: api, changeOrigin: true, rewrite: (p: string) => p.replace(/^\/api/, '') },
  }
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: { port: 5173, strictPort: true, proxy },
    preview: { port: 5173, strictPort: true, proxy },
  }
})
