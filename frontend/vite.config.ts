import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  root: '.',
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:7071',
        changeOrigin: true,
        secure: false
      }
    }
  },
  envPrefix: 'VITE_'
});
