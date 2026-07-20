import { resolve } from 'path';
import { defineConfig } from 'vite';

export default defineConfig({
  root: resolve(__dirname),
  base: '/static/',
  build: {
    outDir: resolve(__dirname, 'backend/static/dist'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        app: resolve(__dirname, 'backend/static/src/js/app.js'),
      },
    },
  },
  server: {
    origin: 'http://localhost:5173',
  },
});
