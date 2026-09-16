// PROTOTYPE — wipe me. Runs only the web app, on its own port, for the session view variants. Their data is a made-up
// fortnight drawn in the browser, so no API, Loki or Tempo is needed.
//
//   node scripts/prototype-sessions.mjs
//
// Ctrl+C stops it.

import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const web = join(root, 'src', 'Skillworks.Studio.Web');
const port = 5180;

const vite = spawn(process.execPath, [join(web, 'node_modules', 'vite', 'bin', 'vite.js'), '--port', String(port), '--strictPort'], {
  cwd: web,
  stdio: 'inherit',
  // Any address quiets the dev server's warning; the prototype never calls /api.
  env: { ...process.env, API_HTTP: 'http://localhost:9' },
});

process.on('SIGINT', () => vite.kill());
process.on('SIGTERM', () => vite.kill());

console.log(`\nOpen http://localhost:${port}/prototype/sessions?variant=A  (Shift + ← → flips variants). Ctrl+C stops it.\n`);
