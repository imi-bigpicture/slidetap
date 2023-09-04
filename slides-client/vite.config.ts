import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      components: '/src/components',
      models: '/src/models',
      services: '/src/services',
    },
  },
  server: {
    port: 13000,
    open: '/',
    proxy: {
      '/api': 'http://127.0.0.1:5001',
    },
  },
})
