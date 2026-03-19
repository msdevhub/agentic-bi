import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: [
      'bi.dev.dora.restry.cn',
      'bi.clawlines.net',
      'bi.dora.restry.cn',
      'localhost',
      '127.0.0.1'
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8899',
        changeOrigin: true
      }
    },
  },
})
