import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    fs: { allow: ['../..'] },
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/fixtures': 'http://127.0.0.1:8000',
      '/v1': { target: 'http://127.0.0.1:8000', ws: true },
    },
  },
});
