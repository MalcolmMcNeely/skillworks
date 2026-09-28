// Not in the Suite: No signal shows only on the developer's own data with the app running.

import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

function option(name, fallback) {
  const at = process.argv.indexOf(`--${name}`);

  return at >= 0 && at + 1 < process.argv.length ? process.argv[at + 1] : fallback;
}

const api = option('api', 'http://localhost:5222');
const loads = Number(option('loads', '15'));

function docker(...args) {
  const result = spawnSync('docker', args, { encoding: 'utf8', maxBuffer: 512 * 1024 * 1024 });

  if (result.status !== 0) {
    throw new Error(`docker ${args.join(' ')} failed: ${result.stderr}`);
  }

  // Loki writes its log to stderr.
  return `${result.stdout}${result.stderr}`;
}

function stop(message) {
  console.error(message);
  process.exit(2);
}

// Aspire names a persistent container for its resource and a suffix of its own.
function lokiContainer() {
  const named = option('loki', null);

  if (named) {
    return named;
  }

  const running = docker('ps', '--filter', 'name=^loki-', '--format', '{{.Names}}').split('\n').filter(Boolean);

  if (running.length !== 1) {
    stop(`Found ${running.length} running Loki containers named loki-*. Name the AppHost's with --loki <name>.`);
  }

  return running[0];
}

// Read from the AppHost's own list, so the check and the app never disagree.
function missingFlags(container) {
  const wanted = [...readFileSync(join(root, 'src', 'Skillworks.AppHost', 'LokiFlags.cs'), 'utf8').matchAll(/"(-[^"=]+=[^"]*)"/g)]
    .map((match) => match[1]);

  // With no flags found, the check would pass any store.
  if (wanted.length === 0) {
    stop('Found no flag written as "-name=value" in src/Skillworks.AppHost/LokiFlags.cs, so the check cannot say what Loki should run with.');
  }

  const running = JSON.parse(docker('inspect', container, '--format', '{{json .Args}}'));

  return wanted.filter((flag) => !running.includes(flag));
}

async function load() {
  const started = performance.now();
  let answer;

  try {
    answer = await (await fetch(new URL('/api/sessions', api))).text();
  } catch (failure) {
    stop(`Studio does not answer at ${api} (${failure.cause?.code ?? failure.message}). Start it with aspire run, or pass its address with --api.`);
  }

  const lines = answer.split('\n').filter(Boolean).map((line) => JSON.parse(line));
  const rows = lines.filter((line) => line.kind === 'sessions').reduce((count, line) => count + line.sessions.length, 0);
  const gap = lines.find((line) => line.kind === 'end')?.gap ?? { kind: 'no end line' };

  return { rows, gap, seconds: (performance.now() - started) / 1000 };
}

// Go writes a duration as 1m2.5s, 312.4ms or 81.2µs.
function seconds(duration) {
  const units = { h: 3600, m: 60, s: 1, ms: 1e-3, us: 1e-6, µs: 1e-6, ns: 1e-9 };

  return [...duration.matchAll(/(\d+(?:\.\d+)?)(ns|us|µs|ms|s|m|h)/g)].reduce((total, [, value, unit]) => total + Number(value) * units[unit], 0);
}

// Each querier line is one part of a query, and queue_time is its wait for a worker.
function queueWaits(container, since) {
  return docker('logs', '--since', since, container)
    .split('\n')
    .filter((line) => line.includes('component=querier'))
    .map((line) => /queue_time=(\S+)/.exec(line)?.[1])
    .filter(Boolean)
    .map(seconds)
    .sort((a, b) => a - b);
}

const container = lokiContainer();
const missing = missingFlags(container);

if (missing.length > 0) {
  stop(
    `${container} runs without ${missing.join(' ')}. A persistent container keeps the flags it was made with.\n` +
      `Stop Aspire, run docker rm -f ${container}, and start Aspire again. Its data stays in its volume.`,
  );
}

const since = new Date().toISOString();
let unreachableLoads = 0;

for (let at = 1; at <= loads; at++) {
  const { rows, gap, seconds: took } = await load();
  const unreachable = gap.kind === 'unreachable';

  if (unreachable) {
    unreachableLoads++;
  }

  const said = unreachable ? `No signal: ${gap.missing ?? 'nothing named'}` : `Gap ${gap.kind}`;

  console.log(`Load ${at} of ${loads}: ${rows} rows, ${said}, ${took.toFixed(1)} s`);
}

const waits = queueWaits(container, since);
const longest = waits.at(-1) ?? 0;
const middle = waits[Math.floor(waits.length / 2)] ?? 0;

console.log(`\n${loads - unreachableLoads} of ${loads} loads ended with no Gap of an unreachable store.`);
console.log(`Loki ran ${waits.length} parts. The longest waited ${longest.toFixed(3)} s in its queue, and the middle one ${middle.toFixed(3)} s.`);

process.exit(unreachableLoads === 0 ? 0 : 1);
