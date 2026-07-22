import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.js'],
  },
  server: {
    port: 5174,
    proxy: {
      '/upload': 'http://localhost:8001',
      '/upload_text': 'http://localhost:8001',
      '/query': 'http://localhost:8001',
      '/investigate': 'http://localhost:8001',
      '/story': 'http://localhost:8001',
      '/predict': 'http://localhost:8001',
      '/predict_input': 'http://localhost:8001',
      '/simulate': 'http://localhost:8001',
      '/scenario_parse': 'http://localhost:8001',
      '/model_info': 'http://localhost:8001',
      '/upload_doc': 'http://localhost:8001',
      '/docs': 'http://localhost:8001',
      '/quality': 'http://localhost:8001',
      '/brief': 'http://localhost:8001',
      '/cleaning_plan': 'http://localhost:8001',
      '/clean': 'http://localhost:8001',
      '/contract': 'http://localhost:8001',
      '/validate_rows': 'http://localhost:8001',
      '/dashboard': 'http://localhost:8001',
      '/benchmark': 'http://localhost:8001',
      '/report': 'http://localhost:8001',
      '/infer_join': 'http://localhost:8001',
      '/join': 'http://localhost:8001',
      '/forecast': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
    }
  }
})
