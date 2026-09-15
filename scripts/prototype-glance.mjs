// PROTOTYPE — wipe me. Runs Studio against a throwaway Loki filled with a made-up month of telemetry, so
// the at-a-glance variants can be judged against realistic volume. The real `skillworks-loki` is never touched.
//
//   node scripts/prototype-glance.mjs              start Loki, seed it, run the API and the web app
//   node scripts/prototype-glance.mjs --seed-only  start Loki and seed it, then exit and leave it running
//
// Ctrl+C stops the API and the web app and removes the Loki container, and its events with it.

import { spawn, spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const container = 'skillworks-prototype-wipe-me-loki';
const lokiPort = 3101;
const apiPort = 5199;
const webPort = 5173;
const loki = `http://localhost:${lokiPort}`;
const seedOnly = process.argv.includes('--seed-only');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function docker(...args) {
  const result = spawnSync('docker', args, { encoding: 'utf8' });

  if (result.status !== 0 && !args.includes('rm')) {
    throw new Error(`docker ${args.join(' ')} failed: ${result.stderr}`);
  }

  return result.stdout.trim();
}

async function startLoki() {
  docker('rm', '-f', container);
  docker(
    'run', '-d', '--rm', '--name', container,
    '-p', `127.0.0.1:${lokiPort}:3100`,
    '-v', `${join(root, 'scripts', 'prototype-glance-loki.yaml')}:/etc/loki/prototype.yaml:ro`,
    'grafana/loki:3.5.9', '-config.file=/etc/loki/prototype.yaml',
  );

  for (let attempt = 0; attempt < 120; attempt++) {
    try {
      if ((await fetch(`${loki}/ready`)).ok) {
        return;
      }
    } catch {}
    await sleep(500);
  }

  throw new Error('The prototype Loki never became ready');
}

// ---- the made-up month ----

// Seeded, so every run draws the same month relative to now.
let state = 20260915;
function random() {
  state |= 0;
  state = (state + 0x6d2b79f5) | 0;
  let t = Math.imul(state ^ (state >>> 15), 1 | state);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

const between = (low, high) => low + random() * (high - low);
const whole = (low, high) => Math.floor(between(low, high + 1));
const pick = (weights) => {
  const entries = Object.entries(weights);
  let roll = random() * entries.reduce((sum, [, weight]) => sum + weight, 0);
  for (const [value, weight] of entries) {
    roll -= weight;
    if (roll <= 0) return value;
  }
  return entries.at(-1)[0];
};
const poisson = (mean) => {
  let count = 0;
  let product = random();
  const limit = Math.exp(-mean);
  while (product > limit) {
    count += 1;
    product *= random();
  }
  return count;
};

const opus = 'claude-opus-5';
const sonnet = 'claude-sonnet-5';
const haiku = 'claude-haiku-4-5-20251001';

// Dollars per million tokens: input, output, cache read, cache creation. Made up for the seed, not a price list.
const rates = {
  [opus]: [5, 25, 0.5, 6.25],
  [sonnet]: [3, 15, 0.3, 3.75],
  [haiku]: [1, 5, 0.1, 1.25],
};

const skills = [
  { name: 'implement', rate: 4.5, turns: [25, 90], models: { [opus]: 1 }, efforts: { xhigh: 3, high: 1 }, triggers: { 'user-slash': 6, 'claude-proactive': 4 } },
  { name: 'code-review', rate: 3.5, turns: [15, 45], models: { [opus]: 1 }, efforts: { xhigh: 1 }, triggers: { 'claude-proactive': 5, 'nested-skill': 4, 'user-slash': 1 } },
  { name: 'comment-sweep', rate: 2.8, turns: [6, 20], models: { [opus]: 2, [sonnet]: 1 }, efforts: { high: 1 }, triggers: { 'nested-skill': 6, 'user-slash': 4 } },
  { name: 'tdd', rate: 2.4, turns: [20, 60], models: { [opus]: 1 }, efforts: { xhigh: 1, high: 1 }, triggers: { 'claude-proactive': 7, 'user-slash': 3 } },
  { name: 'diagnosing-bugs', rate: 1.7, turns: [15, 70], models: { [opus]: 1 }, efforts: { xhigh: 1 }, triggers: { 'claude-proactive': 8, 'user-slash': 2 } },
  { name: 'unslop', rate: 2.1, turns: [2, 6], models: { [haiku]: 3, [sonnet]: 1 }, efforts: { medium: 1 }, triggers: { 'claude-proactive': 5, 'nested-skill': 5 } },
  { name: 'domain-modeling', rate: 1.1, turns: [8, 30], models: { [opus]: 1 }, efforts: { xhigh: 1 }, triggers: { 'claude-proactive': 1 } },
  { name: 'grilling', rate: 0.9, turns: [5, 25], models: { [opus]: 1 }, efforts: { high: 1 }, triggers: { 'claude-proactive': 6, 'user-slash': 4 } },
  { name: 'to-spec', rate: 0.8, turns: [10, 25], models: { [opus]: 1 }, efforts: { xhigh: 1 }, triggers: { 'user-slash': 7, 'claude-proactive': 3 } },
  { name: 'to-tickets', rate: 0.7, turns: [10, 30], models: { [opus]: 3, [haiku]: 1 }, efforts: { xhigh: 1 }, triggers: { 'nested-skill': 6, 'user-slash': 4 } },
  { name: 'research', rate: 0.6, turns: [20, 60], models: { [sonnet]: 1 }, efforts: { high: 1 }, triggers: { 'claude-proactive': 5, 'user-slash': 3, 'agent-preload': 2 } },
  { name: 'writing-for-agents', rate: 0.6, turns: [4, 15], models: { [opus]: 1 }, efforts: { high: 1 }, triggers: { 'nested-skill': 7, 'claude-proactive': 3 } },
  { name: 'prototype', rate: 0.45, turns: [30, 120], models: { [opus]: 1 }, efforts: { xhigh: 1 }, triggers: { 'user-slash': 1 } },
  { name: 'resolving-merge-conflicts', rate: 0.4, turns: [5, 20], models: { [sonnet]: 1 }, efforts: { medium: 1 }, triggers: { 'claude-proactive': 1 } },
  { name: 'codebase-design', rate: 0.3, turns: [10, 40], models: { [opus]: 1 }, efforts: { xhigh: 1 }, triggers: { 'claude-proactive': 5, 'nested-skill': 5 } },
  { name: 'wizard', rate: 0.12, turns: [5, 15], models: { [sonnet]: 1 }, efforts: { medium: 1 }, triggers: { 'user-slash': 1 } },
  { name: 'artifact-design', rate: 0.5, turns: [6, 18], source: 'bundled', models: { [opus]: 1 }, efforts: { high: 1 }, triggers: { 'nested-skill': 8, 'claude-proactive': 2 } },
  { name: 'frontend-design', rate: 0.7, turns: [10, 35], source: 'plugin', plugin: 'frontend-design', marketplace: 'claude-plugins-official', models: { [opus]: 1 }, efforts: { high: 1 }, triggers: { 'claude-proactive': 1 } },
];

const repositories = {
  'malcolm/skillworks': 45,
  'malcolm/podium': 30,
  'acme/billing-api': 15,
  '': 10,
};

const dayMs = 24 * 60 * 60 * 1000;

function turnsFor(model, count, startMs, context) {
  const [inRate, outRate, readRate, writeRate] = rates[model];
  const turns = [];
  let cache = between(20000, 60000);

  for (let index = 0; index < count; index++) {
    const input = whole(1, 60);
    const output = Math.round(Math.exp(between(Math.log(150), Math.log(3500))));
    const cacheCreation = whole(400, index === 0 ? 30000 : 9000);
    const cacheRead = Math.round(cache);
    cache = Math.min(400000, cache + cacheCreation * 0.8);

    const cost = (input * inRate + output * outRate + cacheRead * readRate + cacheCreation * writeRate) / 1e6;

    turns.push({
      at: startMs + (index + 1) * between(8000, 40000),
      attributes: {
        ...context,
        model,
        cost_usd: cost.toFixed(6),
        input_tokens: String(input),
        output_tokens: String(output),
        cache_read_tokens: String(cacheRead),
        cache_creation_tokens: String(cacheCreation),
        request_id: `req_${randomUUID().replaceAll('-', '')}`,
        duration_ms: String(whole(900, 9000)),
        speed: 'normal',
      },
    });
  }

  return turns;
}

function month(now) {
  const firings = [];
  const turns = [];
  const today = Math.floor(now / dayMs) * dayMs;

  for (let back = 29; back >= 0; back--) {
    const day = today - back * dayMs;
    const weekday = new Date(day).getUTCDay();
    const weekend = weekday === 0 ? 0.12 : weekday === 6 ? 0.25 : 1;
    // Usage grows through the month, and one week in the middle is a holiday.
    const growth = 0.55 + (0.65 * (29 - back)) / 29;
    const holiday = back >= 16 && back <= 19 ? 0.2 : 1;
    const volume = weekend * growth * holiday;

    const sessions = Array.from({ length: Math.max(1, poisson(7 * volume)) }, () => ({
      id: randomUUID(),
      repository: pick(repositories),
      startHour: between(7.5, 19),
      sequence: 0,
    }));

    for (const skill of skills) {
      for (let count = poisson(skill.rate * volume); count > 0; count--) {
        const session = sessions[whole(0, sessions.length - 1)];
        const at = day + (session.startHour + between(0, 2.5)) * 60 * 60 * 1000;

        if (at > now) {
          continue;
        }

        const [owner, name] = session.repository === '' ? [undefined, undefined] : session.repository.split('/');
        const place = { 'vcs.owner.name': owner, 'vcs.repository.name': name };

        firings.push({
          at,
          session,
          attributes: {
            'skill.name': skill.name,
            invocation_trigger: pick(skill.triggers),
            'skill.source': skill.source ?? pick({ projectSettings: 3, userSettings: 1 }),
            'plugin.name': skill.plugin,
            'marketplace.name': skill.marketplace,
            ...place,
          },
        });

        const model = pick(skill.models);
        const context = { 'skill.name': skill.name, effort: pick(skill.efforts), ...place };
        for (const turn of turnsFor(model, whole(...skill.turns), at, context)) {
          if (turn.at <= now) turns.push({ ...turn, session });
        }
      }
    }

    // A third-party plugin's turns arrive with the skill unnamed, which Studio shows as one amount of its own.
    for (let count = poisson(1.4 * volume); count > 0; count--) {
      const session = sessions[whole(0, sessions.length - 1)];
      const at = day + (session.startHour + between(0, 3)) * 60 * 60 * 1000;
      for (const turn of turnsFor(sonnet, whole(4, 20), at, { 'skill.name': 'third-party', effort: 'medium' })) {
        if (turn.at <= now) turns.push({ ...turn, session });
      }
    }
  }

  return { firings, turns };
}

function record(eventName, at, session, attributes) {
  session.sequence += 1;
  const nanoseconds = `${BigInt(Math.round(at)) * 1000000n}`;
  const stamp = new Date(at).toISOString();

  return {
    timeUnixNano: nanoseconds,
    observedTimeUnixNano: nanoseconds,
    body: { stringValue: `claude_code.${eventName}` },
    attributes: Object.entries({
      'user.id': 'prototype-user',
      'session.id': session.id,
      'app.version': '2.1.268',
      'terminal.type': 'windows-terminal',
      'event.name': eventName,
      'event.timestamp': stamp,
      'event.sequence': String(session.sequence),
      ...attributes,
    })
      .filter(([, value]) => value !== undefined)
      .map(([key, value]) => ({ key, value: { stringValue: value } })),
  };
}

async function push(records) {
  for (let start = 0; start < records.length; start += 1000) {
    const body = {
      resourceLogs: [
        {
          resource: { attributes: [{ key: 'service.name', value: { stringValue: 'claude-code' } }] },
          scopeLogs: [{ scope: { name: 'com.anthropic.claude_code.events' }, logRecords: records.slice(start, start + 1000) }],
        },
      ],
    };

    const response = await fetch(`${loki}/otlp/v1/logs`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Loki refused a batch with ${response.status}: ${await response.text()}`);
    }
  }
}

async function seed() {
  const { firings, turns } = month(Date.now());
  const events = [
    ...firings.map((firing) => ({ at: firing.at, make: () => record('skill_activated', firing.at, firing.session, firing.attributes) })),
    ...turns.map((turn) => ({ at: turn.at, make: () => record('api_request', turn.at, turn.session, turn.attributes) })),
  ].sort((a, b) => a.at - b.at);

  // Built in time order, so each session's sequence climbs the way Claude Code's does.
  await push(events.map((event) => event.make()));

  const cost = turns.reduce((sum, turn) => sum + Number(turn.attributes.cost_usd), 0);
  console.log(`Seeded ${firings.length} firings and ${turns.length} turns ($${cost.toFixed(2)}) into ${loki}`);
}

// ---- run ----

const children = [];

function stop() {
  for (const child of children) {
    child.kill();
  }
  docker('rm', '-f', container);
  process.exit(0);
}

console.log(`Starting a throwaway Loki on ${loki} ...`);
await startLoki();
await seed();

if (seedOnly) {
  console.log(`Left running. Remove it with: docker rm -f ${container}`);
  process.exit(0);
}

process.on('SIGINT', stop);
process.on('SIGTERM', stop);

children.push(
  spawn('dotnet', ['run', '--project', join(root, 'src', 'Skillworks.Studio.Api'), '--no-launch-profile', '--urls', `http://localhost:${apiPort}`], {
    stdio: 'inherit',
    env: {
      ...process.env,
      ASPNETCORE_ENVIRONMENT: 'Development',
      Loki__Address: loki,
      // A month of this volume takes Loki longer than the API's 5 second default to sum.
      Loki__TimeoutSeconds: '30',
      Catalogue__Path: join(root, 'plugins'),
    },
  }),
);

const web = join(root, 'src', 'Skillworks.Studio.Web');
children.push(
  spawn(process.execPath, [join(web, 'node_modules', 'vite', 'bin', 'vite.js'), '--port', String(webPort), '--strictPort'], {
    cwd: web,
    stdio: 'inherit',
    env: { ...process.env, API_HTTP: `http://localhost:${apiPort}` },
  }),
);

console.log(`\nOpen http://localhost:${webPort}/?variant=A  (← → flips variants). Ctrl+C stops everything and wipes the Loki.\n`);
