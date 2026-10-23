import { defineConfig } from 'vitest/config';

// 8001 by default (8000 is often taken). same variable as the backend in api/__main__.py
const apiPort = process.env.MASAR_PORT ?? '8001';

// no react plugin: vite builds .tsx by itself, we only lose hot state keeping
export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    // the browser talks to one address, vite passes /api on to the backend
    proxy: { '/api': `http://127.0.0.1:${apiPort}` },
  },
  test: { include: ['src/**/*.test.ts'] },
});
