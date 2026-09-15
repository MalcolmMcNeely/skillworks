import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// The AppHost's WithReference(api) injects API_HTTP(S), so no address is written here.
const apiAddress = process.env.API_HTTPS ?? process.env.API_HTTP;

// Without it every /api call would quietly 404 from this dev server instead of reaching the API.
if (!apiAddress && !process.env.VITEST) {
  console.warn('No API address in the environment. Start Studio with `aspire run`.');
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: apiAddress
      ? { '/api': { target: apiAddress, changeOrigin: true, secure: false } }
      : undefined,
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
