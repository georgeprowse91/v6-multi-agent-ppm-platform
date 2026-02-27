import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@design-system': path.resolve(__dirname, '../../../packages/ui-kit/design-system'),
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
    allowedHosts: ['localhost', '127.0.0.1', '.local'],
    proxy: {
      '/v1': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/session': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => '/v1' + path,
      },
      '/config': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => '/v1' + path,
      },
      '/login': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => '/v1' + path,
      },
      '/logout': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => '/v1' + path,
      },
    },
  },
});
