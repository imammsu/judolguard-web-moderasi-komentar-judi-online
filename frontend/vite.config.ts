import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const BACKEND = 'http://127.0.0.1:5000';

// Saat pengembangan, permintaan /api, /auth, dan /health diteruskan ke Flask
// sehingga browser melihat satu origin (cookie HttpOnly + SameSite=Lax tetap jalan).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: false },
      '/auth': { target: BACKEND, changeOrigin: false },
      '/health': { target: BACKEND, changeOrigin: false },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
