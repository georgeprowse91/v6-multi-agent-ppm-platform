import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@design-system': path.resolve(__dirname, '../../../packages/ui-kit/design-system'),
      '@ppm/canvas-engine': path.resolve(__dirname, '../../..', 'packages/canvas-engine/src'),
    },
  },
});
