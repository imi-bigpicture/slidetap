import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      src: '/src',
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