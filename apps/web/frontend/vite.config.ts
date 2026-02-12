import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@design-system': path.resolve(__dirname, '../../../design-system'),
      '@ppm/canvas-engine': path.resolve(__dirname, '../../../packages/canvas-engine/src'),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5000,
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      '/v1': {
        target: 'http://localhost:8501',
        changeOrigin: true,
      },
      '/healthz': {
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
      '/app': {
        target: 'http://localhost:8501',
        changeOrigin: true,
      },
    },
  },
});
