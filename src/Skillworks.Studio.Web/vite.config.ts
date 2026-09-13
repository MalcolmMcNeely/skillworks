import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Aspire's AddViteApp injects API_HTTP(S) from the AppHost's `api` resource, so the address is
// never written down here.
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
