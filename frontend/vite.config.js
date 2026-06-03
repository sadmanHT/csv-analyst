import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/upload': 'http://localhost:8001',
      '/query': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
    }
  }
})
