import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@ppm/canvas-engine': path.resolve(__dirname, '../../../packages/canvas-engine/src'),
    },
  },
  build: {
    outDir: '../static/dist',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8501',
        changeOrigin: true,
      },
      '/config': {
        target: 'http://localhost:8501',
        changeOrigin: true,
      },
      '/session': {
        target: 'http://localhost:8501',
        changeOrigin: true,
      },
      '/login': {
        target: 'http://localhost:8501',
        changeOrigin: true,
      },
      '/logout': {
        target: 'http://localhost:8501',
        changeOrigin: true,
      },
    },
  },
});
