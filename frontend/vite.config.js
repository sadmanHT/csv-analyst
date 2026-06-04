import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/upload': 'http://localhost:8001',
      '/upload_text': 'http://localhost:8001',
      '/query': 'http://localhost:8001',
      '/predict': 'http://localhost:8001',
      '/predict_input': 'http://localhost:8001',
      '/model_info': 'http://localhost:8001',
      '/upload_doc': 'http://localhost:8001',
      '/docs': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
    }
  }
})
