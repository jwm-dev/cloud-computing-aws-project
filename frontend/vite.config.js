import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/experiments': 'http://backend:8000',
      '/analytics': 'http://backend:8000',
      '/replays': 'http://backend:8000',
    },
  },
})
