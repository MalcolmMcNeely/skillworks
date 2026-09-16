// PROTOTYPE — wipe me. A made-up fortnight of sessions across four repositories and five people, seeded so every
// load draws the same fortnight relative to now. Durations, token counts and hook costs follow the real events
// read from the local Loki on 2026-09-15; the words are invented.

import type {
  ContentSwitches,
  ModelStep,
  PromptSpan,
  Said,
  Session,
  SessionStep,
  Thread,
  ToolFamily,
  Trigger,
} from './sessionModel';

const second = 1000;
const minute = 60 * second;
const hour = 60 * minute;
const day = 24 * hour;

const opus = 'claude-opus-5[1m]';
const haiku = 'claude-haiku-4-5-20251001';

// Dollars per million tokens: input, output, cache read, cache write. Made up for the fixture, not a price list.
const rates: Record<string, [number, number, number, number]> = {
  [opus]: [5, 25, 0.5, 6.25],
  [haiku]: [1, 5, 0.1, 1.25],
};

function randomFrom(seed: number) {
  let state = seed | 0;

  const next = () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  const between = (low: number, high: number) => low + next() * (high - low);

  return {
    next,
    between,
    whole: (low: number, high: number) => Math.floor(between(low, high + 1)),
    chance: (odds: number) => next() < odds,
    pick: <T>(items: readonly T[]): T => items[Math.floor(next() * items.length)],
    weighted: <K extends string>(weights: Partial<Record<K, number>>): K => {
      const entries = Object.entries(weights) as [K, number][];
      let roll = next() * entries.reduce((sum, [, weight]) => sum + weight, 0);
      for (const [key, weight] of entries) {
        roll -= weight;
        if (roll <= 0) return key;
      }
      return entries[entries.length - 1][0];
    },
    // Real durations and token counts have long right tails, so draws are log-normal from a median and a 90th percentile.
    skewed: (median: number, p90: number) => {
      const z = Math.sqrt(-2 * Math.log(1 - next())) * Math.cos(2 * Math.PI * next());
      const mu = Math.log(median);
      return Math.exp(mu + ((Math.log(p90) - mu) / 1.2816) * z);
    },
    hex: (length: number) => Array.from({ length }, () => Math.floor(next() * 16).toString(16)).join(''),
  };
}

type Random = ReturnType<typeof randomFrom>;

const said = (shown: boolean, text: string): Said => ({ text: shown ? text : null, length: text.length });

// ---- places and people ----

interface FailingTest {
  name: string;
  command: string;
  output: string;
}

interface Place {
  key: string;
  repository: string;
  folder: string;
  hook: { event: 'PreToolUse' | 'PostToolUse'; matcher: '*' | 'shell'; low: number; high: number; blockRate: number } | null;
  switches: ContentSwitches;
  issues: { ref: string; title: string; change: string }[];
  issueCommand: (ref: string) => string;
  code: string[];
  tests: string[];
  docs: string[];
  patterns: string[];
  testCommand: string;
  passOutput: string;
  failing: FailingTest[];
  snippets: string[];
  questions: string[];
  changes: string[];
  research: string[];
}

const everythingOn: ContentSwitches = { prompts: true, responses: true, toolContent: true };

const places: Record<string, Place> = {
  skillworks: {
    key: 'skillworks',
    repository: 'malcolm/skillworks',
    folder: 'skillworks',
    // A user hook that runs a PowerShell script after every tool call. It costs about 370 ms each time.
    hook: { event: 'PostToolUse', matcher: '*', low: 340, high: 820, blockRate: 0 },
    switches: everythingOn,
    issues: [
      { ref: '58', title: 'A 429 from Loki shows as a Gap', change: 'maps a 429 to StoreUnreachable and names the day' },
      { ref: '61', title: 'The repository picker keeps its choice after a reload', change: 'reads the repository back out of the address' },
      { ref: '64', title: 'Health names the part that is off', change: 'gives every part that is not working its action' },
      { ref: '66', title: 'Hook time shows in the rail', change: 'sums hook_execution_complete per day' },
    ],
    issueCommand: (ref) => `gh issue view ${ref} --comments`,
    code: [
      'src/Skillworks.Core/EventsStore/LokiEventsStore.cs',
      'src/Skillworks.Core/Activations/Queries/ActivationQueries.cs',
      'src/Skillworks.Studio.Api/Skills/SkillEndpoints.cs',
      'src/Skillworks.Studio.Api/Health/HealthEndpoints.cs',
      'src/Skillworks.Studio.Web/src/skills/lib/map.ts',
      'src/Skillworks.Studio.Web/src/filters/lib/filters.ts',
      'src/Skillworks.Studio.Web/src/skills/components/SkillMap.tsx',
      'src/Skillworks.Studio.Web/src/styles.css',
    ],
    tests: [
      'tests/Skillworks.Studio.Api.Tests/Skills/SkillEndpoints.Gaps.Tests.cs',
      'tests/Skillworks.Core.Tests/EventsStore/LokiEventsStore.Tests.cs',
      'src/Skillworks.Studio.Web/src/skills/lib/map.test.ts',
    ],
    docs: ['CONTEXT.md', 'docs/adr/0006-events-store-answers-arrive-day-by-day.md', 'docs/agents/issue-tracker.md', '.claude/rules/file-placement.md'],
    patterns: ['StoreUnreachable', 'TimeoutSeconds', 'foldSkillsLine', 'RepositoryPicker', 'ReadDays'],
    testCommand: 'dotnet test tests/Skillworks.Studio.Api.Tests',
    passOutput: 'Passed!  - Failed:     0, Passed:   142, Skipped:     0, Total:   142, Duration: 9 s - Skillworks.Studio.Api.Tests.dll (net10.0)',
    failing: [
      {
        name: 'A_store_that_stops_part_way_keeps_its_days',
        command: 'dotnet test tests/Skillworks.Studio.Api.Tests --filter A_store_that_stops_part_way_keeps_its_days | Select-String -Pattern "Failed|Passed"',
        output: [
          '  Failed Skillworks.Studio.Api.Tests.Skills.SkillEndpointsGapsTests.A_store_that_stops_part_way_keeps_its_days [412 ms]',
          '  Error Message:',
          '   Expected answer.Days to contain 3 item(s), but found 2: {2026-09-13, 2026-09-14}.',
          '  Stack Trace:',
          '     at SkillEndpointsGapsTests.A_store_that_stops_part_way_keeps_its_days() in SkillEndpoints.Gaps.Tests.cs:line 88',
          '',
          'Failed!  - Failed:     1, Passed:   141, Skipped:     0, Total:   142, Duration: 9 s',
        ].join('\n'),
      },
      {
        name: 'Loki_off_is_off_not_broken',
        command: 'dotnet test tests/Skillworks.Studio.Api.Tests --filter Loki_off_is_off_not_broken',
        output: [
          '  Failed Skillworks.Studio.Api.Tests.Health.HealthEndpointsTests.Loki_off_is_off_not_broken [233 ms]',
          '  Error Message:',
          '   Expected part.State to be "off", but found "broken".',
          '',
          'Failed!  - Failed:     1, Passed:   141, Skipped:     0, Total:   142, Duration: 8 s',
        ].join('\n'),
      },
    ],
    snippets: [
      [
        'public async IAsyncEnumerable<DayAnswer> ReadDays(Filter filter, [EnumeratorCancellation] CancellationToken cancel)',
        '{',
        '    foreach (var day in filter.Span.Days())',
        '    {',
        '        var answer = await ReadDay(day, cancel);',
        '        yield return answer;',
        '',
        '        if (answer.Gap is StoreUnreachable)',
        '        {',
        '            yield break;',
        '        }',
        '    }',
        '}',
      ].join('\n'),
      [
        'export function foldSkillsLine(answer: SkillsAnswer | null, line: SkillsLine): SkillsAnswer {',
        "  if (line.kind === 'day') {",
        '    return { ...answer, days: [...(answer?.days ?? []), line.day], arriving: true };',
        '  }',
        '',
        '  return { ...answer, gap: line.gap, arriving: false };',
        '}',
      ].join('\n'),
      [
        'app.MapGet("/api/health", async (HealthCheck health, CancellationToken cancel) =>',
        '{',
        '    var parts = await health.ReadParts(cancel);',
        '    return Results.Ok(parts.Select(part => new PartResponse(part.Name, part.State, part.Action)));',
        '});',
      ].join('\n'),
    ],
    questions: [
      'is the Loki timeout still 5 seconds?',
      'what does ADR 6 say about live views?',
      'how do I run only the web tests?',
      'why does the architecture test count the css files?',
      'which endpoint does the repository picker call?',
    ],
    changes: [
      'the rail totals wrap on a small laptop, make them fit',
      'rename describeSpan to spanWords everywhere',
      'the Gap sentence says "quiet" when Loki is down, fix it',
      'add the hook time to the rail under Cost',
    ],
    research: ['how Tempo finds traces by a span attribute with TraceQL', 'the Collector traces pipeline for Tempo'],
  },
  podium: {
    key: 'podium',
    repository: 'malcolm/podium',
    folder: 'podium',
    hook: { event: 'PreToolUse', matcher: 'shell', low: 40, high: 130, blockRate: 0 },
    switches: everythingOn,
    issues: [
      { ref: '212', title: 'Rooms drop the last message on reconnect', change: 'replays from the cursor, not after it' },
      { ref: '219', title: 'Rate-limit joins per IP', change: 'adds a token bucket in front of join' },
      { ref: '224', title: 'Move presence to Redis streams', change: 'writes presence to a stream per room' },
    ],
    issueCommand: (ref) => `gh issue view ${ref}`,
    code: ['src/rooms/roomQueue.ts', 'src/rooms/presence.ts', 'src/http/server.ts', 'src/limits/joinLimiter.ts', 'package.json'],
    tests: ['src/rooms/roomQueue.test.ts', 'src/limits/joinLimiter.test.ts'],
    docs: ['README.md', 'docs/architecture.md'],
    patterns: ['replayFrom', 'joinLimiter', 'XADD', 'onReconnect'],
    testCommand: 'pnpm vitest run',
    passOutput: ' Test Files  12 passed (12)\n      Tests  97 passed (97)\n   Duration  3.12s',
    failing: [
      {
        name: 'replays the last message after a reconnect',
        command: 'pnpm vitest run src/rooms',
        output: [
          ' FAIL  src/rooms/roomQueue.test.ts > RoomQueue > replays the last message after a reconnect',
          "AssertionError: expected [ 'm1', 'm2' ] to deeply equal [ 'm1', 'm2', 'm3' ]",
          ' ❯ src/rooms/roomQueue.test.ts:41:32',
          '',
          ' Test Files  1 failed | 11 passed (12)',
          '      Tests  1 failed | 96 passed (97)',
        ].join('\n'),
      },
    ],
    snippets: [
      [
        'export class RoomQueue {',
        '  private readonly buffer: Message[] = [];',
        '',
        '  replayFrom(cursor: number): Message[] {',
        '    return this.buffer.filter((message) => message.seq > cursor);',
        '  }',
        '}',
      ].join('\n'),
      [
        'export function joinLimiter(perMinute: number) {',
        '  const buckets = new Map<string, number>();',
        '  return (ip: string) => (buckets.get(ip) ?? perMinute) > 0;',
        '}',
      ].join('\n'),
    ],
    questions: ['where do we close the socket on a failed join?', 'what is the Redis key shape for presence?', 'why is pnpm install slow on CI?'],
    changes: ['log the room id on every dropped message', 'bump the join limit to 30 a minute', 'make the reconnect test less flaky'],
    research: ['Redis streams consumer groups for presence'],
  },
  billing: {
    key: 'billing',
    repository: 'acme/billing-api',
    folder: 'billing-api',
    // An organisation policy hook that checks every tool call first, and now and then blocks one.
    hook: { event: 'PreToolUse', matcher: '*', low: 90, high: 280, blockRate: 0.015 },
    // The organisation keeps words out of the shared store. Lengths still arrive.
    switches: { prompts: false, responses: false, toolContent: false },
    issues: [
      { ref: 'BILL-1432', title: 'Proration is off by a day at month end', change: 'counts days from the first of the month' },
      { ref: 'BILL-1440', title: 'Idempotency keys expire too early', change: 'moves the key TTL to 24 hours' },
    ],
    issueCommand: (ref) => `jira issue view ${ref}`,
    code: ['internal/invoice/ledger.go', 'internal/invoice/proration.go', 'internal/idempotency/store.go', 'cmd/api/main.go', 'migrations/0042_idempotency_ttl.sql'],
    tests: ['internal/invoice/proration_test.go', 'internal/idempotency/store_test.go'],
    docs: ['README.md', 'docs/runbooks/proration.md'],
    patterns: ['ProrateCents', 'daysIn', 'IdempotencyTTL'],
    testCommand: 'go test ./internal/...',
    passOutput: 'ok  \tgithub.com/acme/billing-api/internal/invoice\t0.388s\nok  \tgithub.com/acme/billing-api/internal/idempotency\t0.214s',
    failing: [
      {
        name: 'TestProrationAtMonthEnd',
        command: 'go test ./internal/invoice/... -run TestProrationAtMonthEnd',
        output: [
          '--- FAIL: TestProrationAtMonthEnd (0.00s)',
          '    proration_test.go:88: ProrateCents(3100, 2026-08-31, 2026-09-30) = 3000, want 3100',
          'FAIL',
          'FAIL\tgithub.com/acme/billing-api/internal/invoice\t0.412s',
        ].join('\n'),
      },
    ],
    snippets: [
      [
        'func ProrateCents(amount int64, from, to time.Time) int64 {',
        '\tdays := int64(to.Sub(from).Hours() / 24)',
        '\tmonth := daysIn(from)',
        '\treturn amount * days / month',
        '}',
      ].join('\n'),
    ],
    questions: ['what does the ledger do with a negative line?', 'where is the idempotency TTL set?', 'which migrations touch invoices?'],
    changes: ['add a test for a leap year February', 'return 409 when the idempotency key is reused with a new body'],
    research: ['how other billing systems prorate at month end'],
  },
  scratch: {
    key: 'scratch',
    repository: '',
    folder: 'scratch',
    hook: null,
    switches: everythingOn,
    issues: [{ ref: '-', title: 'Tidy the notes', change: 'sorts the notes by date' }],
    issueCommand: () => 'ls',
    code: ['notes.md', 'convert.py'],
    tests: ['convert_test.py'],
    docs: ['notes.md'],
    patterns: ['TODO'],
    testCommand: 'python -m pytest -q',
    passOutput: '4 passed in 0.08s',
    failing: [{ name: 'test_convert', command: 'python -m pytest -q', output: 'FAILED convert_test.py::test_convert - KeyError: "date"\n1 failed, 3 passed in 0.09s' }],
    snippets: ['const pattern = /^(?<owner>[\\w.-]+)\\/(?<name>[\\w.-]+?)(?:\\.git)?$/;'],
    questions: ['what does this regex match exactly?', 'turn the CSV in notes.md into a markdown table', 'what is the difference between cache read and cache write tokens?'],
    changes: ['make convert.py skip rows with no date'],
    research: ['what OTEL_LOG_RAW_API_BODIES sends'],
  },
};

interface Person {
  handle: string;
  root: string;
  separator: '\\' | '/';
  shell: 'PowerShell' | 'Bash';
  terminal: string;
  places: Partial<Record<string, number>>;
  perDay: number;
  scripted: boolean;
}

const people: Person[] = [
  { handle: 'malcolm', root: 'C:\\Projects', separator: '\\', shell: 'PowerShell', terminal: 'windows-terminal', places: { skillworks: 8, podium: 2, scratch: 1 }, perDay: 2.4, scripted: false },
  { handle: 'priya.n', root: '/Users/priya/code', separator: '/', shell: 'Bash', terminal: 'iTerm.app', places: { podium: 6, billing: 3, scratch: 1 }, perDay: 1.8, scripted: false },
  { handle: 'sam.okafor', root: '/home/sam/src', separator: '/', shell: 'Bash', terminal: 'vscode', places: { billing: 7, skillworks: 2 }, perDay: 1.7, scripted: false },
  { handle: 'lena.wu', root: 'D:\\work', separator: '\\', shell: 'PowerShell', terminal: 'vscode', places: { skillworks: 4, podium: 4, scratch: 2 }, perDay: 1.4, scripted: false },
  { handle: 'ci-runner', root: '/runner/work', separator: '/', shell: 'Bash', terminal: 'non-interactive', places: { skillworks: 3, billing: 2 }, perDay: 1.2, scripted: true },
];

type Shape = 'quick' | 'feature' | 'day' | 'spiral' | 'research' | 'scripted';

// ---- one session ----

interface Tool {
  tool: string;
  family: ToolFamily;
  summary: string;
  input: Record<string, unknown>;
  output: string;
  ok: boolean;
  ms: number;
  tokens: number;
}

interface Context {
  cached: number;
  fresh: number;
  lastAt: number;
}

interface Runner {
  thread: Thread;
  parent: () => string | null;
  agent: string | null;
  purpose: string;
  querySource: string;
  model: string;
  context: Context;
}

function buildSession(random: Random, place: Place, person: Person, startMs: number, shape: Shape): Session {
  const steps: SessionStep[] = [];
  const prompts: PromptSpan[] = [];
  const scripted = shape === 'scripted';
  const effort = random.pick(['xhigh', 'xhigh', 'high']);
  let made = 0;
  let clock = startMs;
  let promptIndex = -1;
  let promptId: string | null = null;
  let skill: string | null = null;
  let title: string | null = null;
  let lastRateLimit = 0;

  const id = (prefix: string) => `${prefix}${(made += 1).toString(36)}`;
  const path = (relative: string) => [person.root, place.folder, ...relative.split('/')].join(person.separator);

  const main: Runner = {
    thread: 'main',
    parent: () => promptId,
    agent: null,
    purpose: 'main thread',
    querySource: scripted ? 'sdk' : 'repl_main_thread',
    model: opus,
    context: { cached: 0, fresh: random.whole(15000, 22000), lastAt: 0 },
  };

  // ---- the model ----

  const callModel = (on: Runner, at: number, text: string | null, stopReason: ModelStep['stopReason'], toolCount: number, attempt = 1): ModelStep => {
    const context = on.context;
    let cacheRead = context.cached;
    let cacheWrite = context.fresh;

    // The prompt cache lives five minutes, so a call after a longer pause writes the whole context again.
    if (context.lastAt > 0 && at - context.lastAt > 5 * minute && cacheRead > 14000) {
      cacheWrite += cacheRead - 12000;
      cacheRead = 12000;
    }

    const inputTokens = random.whole(1, 12);
    const outputTokens =
      on.thread === 'side' && on.purpose !== 'compact'
        ? random.whole(12, 160)
        : Math.min(12000, Math.max(8, Math.round(text === null ? random.skewed(420, 2600) : text.length / 3.6 + random.whole(200, 1400))));
    const ttftMs = Math.round(random.skewed(1150, 1900));
    const ms = Math.round(ttftMs + outputTokens * random.between(8, 15));
    const [inRate, outRate, readRate, writeRate] = rates[on.model];

    const step: ModelStep = {
      kind: 'model',
      id: id('m'),
      parent: on.parent(),
      prompt: promptIndex,
      at: at + ms,
      ms,
      agent: on.agent,
      thread: on.thread,
      purpose: on.purpose,
      querySource: on.querySource,
      model: on.model,
      effort: on.thread === 'side' ? 'none' : effort,
      ttftMs,
      inputTokens,
      outputTokens,
      cacheReadTokens: cacheRead,
      cacheCreationTokens: cacheWrite,
      costUsd: (inputTokens * inRate + outputTokens * outRate + cacheRead * readRate + cacheWrite * writeRate) / 1e6,
      skill: on.thread === 'side' ? null : skill,
      stopReason,
      attempt,
      requestId: `req_${random.hex(24)}`,
      said: text === null ? null : said(place.switches.responses, text),
      toolUseIds: Array.from({ length: toolCount }, () => `toolu_${random.hex(22)}`),
    };

    context.cached = cacheRead + cacheWrite + inputTokens;
    context.fresh = outputTokens;
    context.lastAt = step.at;
    steps.push(step);

    return step;
  };

  const sideCall = (purpose: string, at: number, model: string, text: string | null, context = random.whole(700, 4000)) =>
    callModel(
      { thread: 'side', parent: () => promptId, agent: null, purpose, querySource: purpose, model, context: { cached: 0, fresh: context, lastAt: 0 } },
      at,
      text,
      'end_turn',
      0,
    );

  // ---- tools ----

  const runTools = (on: Runner, call: ModelStep, tools: Tool[], at: number): number => {
    let end = at;

    tools.forEach((spec, index) => {
      const toolId = id('t');
      let start = at + random.whole(2, 40);
      const asks = !scripted && on.thread === 'main' && spec.family === 'shell' && random.chance(0.2);

      if (asks && random.chance(0.07)) {
        const waited = Math.round(random.skewed(6000, 25000));
        steps.push({ kind: 'rejected', id: toolId, parent: on.parent(), prompt: promptIndex, at: start + waited, ms: waited, agent: on.agent, tool: spec.tool, source: 'user_reject', summary: spec.summary });
        on.context.fresh += 60;
        end = Math.max(end, start + waited);
        return;
      }

      const waitedMs = asks ? Math.round(random.skewed(4000, 32000)) : 0;
      const hook = place.hook;
      const hooked = hook !== null && (hook.matcher === '*' || spec.family === 'shell');
      let ok = spec.ok;
      let errorType: string | null = ok ? null : 'ShellError';
      let error: string | null = ok ? null : 'Shell command failed';
      let output = spec.output;

      if (hooked && hook.event === 'PreToolUse') {
        const hookMs = random.whole(hook.low, hook.high);
        const blocked = random.chance(hook.blockRate);
        steps.push({ kind: 'hook', id: id('h'), parent: toolId, prompt: promptIndex, at: start + hookMs, ms: hookMs, agent: on.agent, hook: `PreToolUse:${spec.tool}`, hooks: 1, blocking: blocked ? 1 : 0, errors: 0 });
        start += hookMs;

        if (blocked) {
          ok = false;
          errorType = 'HookBlocked';
          error = 'Blocked by PreToolUse hook: policy/no-secrets';
          output = 'The policy hook blocked this call: it reads a file that matches .env*';
        }
      }

      const runMs = ok || errorType === 'ShellError' ? Math.max(1, Math.round(spec.ms)) : 2;
      const toolAt = start + waitedMs + runMs;

      steps.push({
        kind: 'tool',
        id: toolId,
        parent: on.parent(),
        prompt: promptIndex,
        at: toolAt,
        ms: waitedMs + runMs,
        agent: on.agent,
        tool: spec.tool,
        family: spec.family,
        ok,
        errorType,
        error,
        summary: spec.summary,
        input: JSON.stringify(spec.input, null, 2),
        output: place.switches.toolContent ? output : null,
        inputBytes: JSON.stringify(spec.input).length,
        outputBytes: output.length,
        waitedMs,
        allowedBy: scripted ? 'config' : waitedMs > 0 ? 'user_temporary' : 'config',
        toolUseId: call.toolUseIds[index] ?? `toolu_${random.hex(22)}`,
      });

      let done = toolAt;

      if (hooked && hook.event === 'PostToolUse') {
        const hookMs = Math.round(random.chance(0.85) ? random.between(hook.low, hook.low + 80) : random.between(hook.low + 300, hook.high));
        steps.push({ kind: 'hook', id: id('h'), parent: toolId, prompt: promptIndex, at: toolAt + hookMs, ms: hookMs, agent: on.agent, hook: `PostToolUse:${spec.tool}`, hooks: 1, blocking: 0, errors: 0 });
        done += hookMs;
      }

      on.context.fresh += spec.tokens;
      end = Math.max(end, done);
    });

    return end;
  };

  const excerpt = () => {
    const first = random.whole(1, 180);
    return random
      .pick(place.snippets)
      .split('\n')
      .map((line, index) => `${first + index}\t${line}`)
      .join('\n');
  };

  const tools = {
    read: (relative: string): Tool => ({ tool: 'Read', family: 'read', summary: path(relative), input: { file_path: path(relative) }, output: excerpt(), ok: true, ms: random.whole(2, 14), tokens: random.whole(900, 7000) }),
    grep: (pattern: string): Tool => ({
      tool: 'Grep',
      family: 'read',
      summary: `${pattern}  in ${path('src')}`,
      input: { pattern, path: path('src'), output_mode: 'content' },
      output: place.code
        .slice(0, random.whole(1, 4))
        .map((file) => `${path(file)}:${random.whole(10, 200)}:    ${pattern}(${random.pick(['answer', 'filter', 'day', 'cancel'])})`)
        .join('\n'),
      ok: true,
      ms: random.whole(50, 140),
      tokens: random.whole(200, 1800),
    }),
    glob: (pattern: string): Tool => ({ tool: 'Glob', family: 'read', summary: pattern, input: { pattern }, output: place.code.map(path).join('\n'), ok: true, ms: random.whole(70, 190), tokens: random.whole(150, 600) }),
    edit: (relative: string): Tool => ({
      tool: 'Edit',
      family: 'edit',
      summary: path(relative),
      input: { file_path: path(relative), old_string: random.pick(place.snippets).split('\n')[random.whole(0, 3)] ?? '', new_string: '// changed' },
      output: `The file ${path(relative)} has been updated successfully.`,
      ok: true,
      ms: random.chance(0.85) ? random.whole(8, 40) : random.whole(100, 500),
      tokens: random.whole(80, 400),
    }),
    write: (relative: string, text: string): Tool => ({ tool: 'Write', family: 'edit', summary: path(relative), input: { file_path: path(relative), content: text }, output: `File created successfully at: ${path(relative)}`, ok: true, ms: random.whole(9, 130), tokens: random.whole(60, 200) }),
    shell: (command: string, output: string, ok = true, ms = /test|vitest|pytest/.test(command) ? random.skewed(8500, 19000) : random.skewed(990, 3200)): Tool => ({
      tool: person.shell,
      family: 'shell',
      summary: command,
      input: { command, description: command.split(' ').slice(0, 3).join(' ') },
      output,
      ok,
      ms,
      tokens: Math.ceil(output.length / 3.5) + 40,
    }),
    fetch: (url: string, question: string): Tool => ({ tool: 'WebFetch', family: 'read', summary: url, input: { url, prompt: question }, output: `The page says ${question.toLowerCase()} is set per query with a start and end in nanoseconds.`, ok: random.chance(0.94), ms: random.skewed(900, 6000), tokens: random.whole(400, 2500) }),
    search: (query: string): Tool => ({ tool: 'WebSearch', family: 'read', summary: query, input: { query }, output: `1. ${query} - Grafana documentation\n2. ${query} - GitHub discussion`, ok: true, ms: random.skewed(1800, 4500), tokens: random.whole(600, 2000) }),
  };

  const narration = [
    'Reading the issue and its parent spec first.',
    'Running the new test on its own. It should fail.',
    'The test expects 3 days but the store returns 2. Checking where the loop stops.',
    'Two files need the change. Editing both.',
    'Tests pass. Running the lint before I commit.',
    'Looking for every place that reads the timeout.',
    'That edit did not change the result. Reading the test again.',
  ];

  // ---- the main thread ----

  const act = (text: string | null, work: Tool[]) => {
    if (on429()) {
      return act(text, work);
    }

    const call = callModel(main, clock, text ?? (random.chance(0.35) ? random.pick(narration) : null), 'tool_use', work.length);
    clock = runTools(main, call, work, call.at) + random.whole(30, 400);
  };

  const on429 = () => {
    if (clock - lastRateLimit < 20 * minute || !random.chance(0.004)) {
      return false;
    }

    const ms = random.whole(420, 520);
    steps.push({ kind: 'modelError', id: id('e'), parent: promptId, prompt: promptIndex, at: clock + ms, ms, agent: null, model: opus, status: 429, message: "This request would exceed your account's rate limit. Please try again later.", attempt: 1 });
    lastRateLimit = clock;
    clock += ms + random.whole(2000, 9000);
    return true;
  };

  const answer = (text: string) => {
    on429();
    const call = callModel(main, clock, text, 'end_turn', 0);
    clock = call.at;

    if (!scripted && random.chance(0.45)) {
      sideCall('prompt_suggestion', clock + 30, opus, null, random.whole(2000, 5000));
    }

    if (main.context.cached > 520000) {
      const compact = callModel({ ...main, thread: 'side', purpose: 'compact', querySource: 'compact' }, clock + 200, 'Summary of the conversation so far, kept for the next part of the session.', 'end_turn', 0);
      main.context = { cached: 0, fresh: 26000 + compact.outputTokens, lastAt: 0 };
      clock = compact.at;
    }
  };

  const ask = (text: string, command: string | null = null) => {
    const lastEnd = steps.reduce((latest, step) => Math.max(latest, step.at), startMs);

    const away = !scripted && promptIndex >= 0 && clock - lastEnd > 15 * minute;

    promptIndex += 1;
    promptId = id('p');
    skill = null;
    steps.push({ kind: 'prompt', id: promptId, parent: null, prompt: promptIndex, at: clock, ms: 0, agent: null, said: said(place.switches.prompts, text), command });
    main.context.fresh += Math.ceil(text.length / 3.5);

    // Claude Code writes the recap as the developer comes back, so it belongs to the prompt they come back to.
    if (away) {
      sideCall('away_summary', clock - random.whole(3000, 9000), opus, 'While you were away: the fix for the failing test is in, and the review is still open.', random.whole(30000, 90000));
    }

    if (promptIndex === 0) {
      sideCall('generate_session_title', clock + 60, haiku, title);
    }

    clock += random.whole(40, 250);
  };

  const pause = (ms: number) => {
    clock += Math.round(ms);
  };

  const typed = (name: string) => {
    steps.push({ kind: 'skill', id: id('s'), parent: promptId, prompt: promptIndex, at: clock, ms: 0, agent: null, skill: name, trigger: 'user-slash', source: 'projectSettings', plugin: null });
    skill = name;
    main.context.fresh += random.whole(2500, 7000);
  };

  const useSkill = (name: string, trigger: Trigger, source = 'projectSettings') => {
    const call = callModel(main, clock, null, 'tool_use', 1);
    const end = runTools(main, call, [{ tool: 'Skill', family: 'skill', summary: name, input: { skill: name }, output: `Launching skill: ${name}`, ok: true, ms: random.whole(4, 20), tokens: random.whole(2500, 7000) }], call.at);
    const toolStep = steps.findLast((step) => step.kind === 'tool');
    steps.push({ kind: 'skill', id: id('s'), parent: promptId, prompt: promptIndex, at: toolStep?.at ?? end, ms: 0, agent: null, skill: name, trigger, source, plugin: null });
    skill = name;
    clock = end + random.whole(30, 300);
  };

  interface Task {
    type: string;
    description: string;
    calls: number;
    work: () => Tool[];
    report: string;
  }

  const delegate = (text: string, tasks: Task[], background: boolean) => {
    const call = callModel(main, clock, text, 'tool_use', tasks.length);
    const launch = call.at;
    const ends: number[] = [];

    tasks.forEach((task, index) => {
      const toolId = id('t');
      const agentStepId = id('a');
      const agentId = `a${random.hex(15)}`;
      const model = task.type === 'general-purpose' ? opus : haiku;
      const sub: Runner = {
        thread: 'subagent',
        parent: () => agentStepId,
        agent: agentId,
        purpose: task.type,
        querySource: `agent:builtin:${task.type}`,
        model,
        context: { cached: 0, fresh: random.whole(9000, 16000), lastAt: 0 },
      };
      const begin = launch + random.whole(20, 400);
      let subClock = begin;
      let subTools = 0;
      let tokens = 0;

      for (let turn = 0; turn < task.calls; turn += 1) {
        const work = task.work();
        const subCall = callModel(sub, subClock, null, 'tool_use', work.length);
        tokens += subCall.outputTokens + subCall.cacheCreationTokens;
        subClock = runTools(sub, subCall, work, subCall.at) + random.whole(20, 200);
        subTools += work.length;
      }

      const last = callModel(sub, subClock, task.report, 'end_turn', 0);
      subClock = last.at;
      tokens += last.outputTokens;

      steps.push({ kind: 'subagent', id: agentStepId, parent: toolId, prompt: promptIndex, at: subClock, ms: subClock - begin, agent: null, agentType: task.type, description: task.description, agentId, model, tokens: tokens + sub.context.cached, toolUses: subTools, async: background });

      const toolAt = background ? launch + random.whole(2, 6) : subClock;
      const output = background ? `Async agent launched successfully. agentId: ${agentId}` : task.report;
      steps.push({
        kind: 'tool',
        id: toolId,
        parent: promptId,
        prompt: promptIndex,
        at: toolAt,
        ms: toolAt - launch,
        agent: null,
        tool: 'Agent',
        family: 'agent',
        ok: true,
        errorType: null,
        error: null,
        summary: `${task.type}: ${task.description}`,
        input: JSON.stringify({ subagent_type: task.type, description: task.description, run_in_background: background }, null, 2),
        output: place.switches.toolContent ? output : null,
        inputBytes: 180 + task.description.length,
        outputBytes: output.length,
        waitedMs: 0,
        allowedBy: 'config',
        toolUseId: call.toolUseIds[index],
      });

      if (place.hook?.event === 'PostToolUse') {
        const hookMs = random.whole(place.hook.low, place.hook.low + 60);
        steps.push({ kind: 'hook', id: id('h'), parent: toolId, prompt: promptIndex, at: toolAt + hookMs, ms: hookMs, agent: null, hook: 'PostToolUse:Agent', hooks: 1, blocking: 0, errors: 0 });
      }

      main.context.fresh += Math.ceil(task.report.length / 3.5) + 400;
      ends.push(subClock);
    });

    clock = background ? launch + random.whole(600, 2500) : Math.max(...ends) + random.whole(300, 900);

    if (background) {
      if (random.chance(0.6)) {
        act('While the reviews run, checking the web tests.', [tools.shell(`${place.testCommand}`, place.passOutput)]);
      }
      clock = Math.max(clock, ...ends) + random.whole(800, 4000);
    }
  };

  // ---- the shapes ----

  const code = random.pick(place.code);
  const otherCode = random.pick(place.code.filter((file) => file !== code)) ?? code;
  const test = random.pick(place.tests);
  const failing = random.pick(place.failing);
  const issue = random.pick(place.issues);

  const reviewTask = (axis: string): Task => ({
    type: 'general-purpose',
    description: `Review ${axis.toLowerCase()} since ${random.hex(7)}`,
    calls: random.whole(9, 26),
    work: () =>
      random.pick([
        [tools.shell('git diff HEAD~1 --stat', ` ${code} | 24 ++--\n ${test} | 41 +++++\n 2 files changed`)],
        [tools.read(code), tools.read(test)],
        [tools.grep(random.pick(place.patterns))],
        [tools.read(random.pick(place.docs))],
      ]),
    report: `${axis} review: 2 findings.\n1. ${code}:42 has a comment that says what the next line does.\n2. ${test} reads the timeout twice.`,
  });

  const testCycle = (fails: boolean) => {
    act(null, [tools.edit(test)]);
    act(random.chance(0.5) ? 'Running the new test on its own. It should fail.' : null, [tools.shell(failing.command, failing.output, false)]);
    for (let edit = random.whole(1, 3); edit > 0; edit -= 1) {
      act(null, random.chance(0.3) ? [tools.edit(code), tools.edit(otherCode)] : [tools.edit(code)]);
    }
    if (fails) {
      act(null, [tools.shell(place.testCommand, failing.output, false)]);
      act('Still red. The loop stops one day early.', [tools.read(code)]);
      act(null, [tools.edit(code)]);
    }
    act(null, [tools.shell(place.testCommand, place.passOutput)]);
  };

  const shapes: Record<Shape, () => void> = {
    quick: () => {
      title = random.pick(place.questions).replace(/\?$/, '');
      for (let turn = random.whole(1, 3); turn > 0; turn -= 1) {
        ask(random.pick(place.questions));
        for (let look = random.whole(0, 2); look > 0; look -= 1) {
          act(null, random.chance(0.5) ? [tools.grep(random.pick(place.patterns))] : [tools.read(random.pick(place.code))]);
        }
        answer(`It is set in ${code}. The value comes from configuration first and falls back to the default in the constructor, so a test can pass a shorter one.`);
        pause(random.skewed(45 * second, 4 * minute));
      }
    },

    feature: () => {
      title = issue.title;
      ask(`/implement ${issue.ref}`, 'implement');
      typed('implement');
      act('Reading the issue and its parent spec first.', [tools.shell(place.issueCommand(issue.ref), `${issue.ref} ${issue.title} [open]\n\nThe change ${issue.change}.`)]);
      act(null, [tools.read(random.pick(place.docs)), tools.read(code)]);
      act(null, [tools.grep(random.pick(place.patterns)), tools.glob('**/*.Tests.cs')]);
      for (let look = random.whole(2, 6); look > 0; look -= 1) {
        act(null, random.chance(0.5) ? [tools.read(random.pick(place.code)), tools.read(random.pick(place.tests))] : [tools.grep(random.pick(place.patterns))]);
      }
      useSkill('tdd', 'nested-skill');
      for (let cycle = random.whole(2, 4); cycle > 0; cycle -= 1) {
        testCycle(random.chance(0.3));
      }
      useSkill('comment-sweep', 'nested-skill', random.pick(['projectSettings', 'userSettings']));
      act(null, [tools.shell('git diff --stat', ` ${code} | 24 ++--\n ${test} | 41 +++++`)]);
      act(null, [tools.edit(code), tools.edit(test)]);
      useSkill('code-review', 'nested-skill');
      delegate('Starting three reviews in parallel: standards, spec and architecture.', ['Standards', 'Spec', 'Architecture'].map(reviewTask), true);
      act('Two findings are real. Fixing both.', [tools.edit(otherCode)]);
      act(null, [tools.shell(place.testCommand, place.passOutput)]);
      act(null, [tools.shell(`git commit -m "${issue.title}"`, `[main ${random.hex(7)}] ${issue.title}\n 3 files changed, 71 insertions(+), 12 deletions(-)`)]);
      act(null, [tools.shell('git push', 'To github.com:malcolm/skillworks.git\n   9727980..4b1e2a7  main -> main')]);
      answer(
        `Done. ${issue.ref} is in.\n\nWhat changed:\n- ${code}: ${issue.change}.\n- ${test}: a new test for it.\n\nThe code review found 2 things. I fixed both: a comment that said what the code does, and a timeout read twice. All tests pass. Pushed.`,
      );

      if (!scripted && random.chance(0.7)) {
        pause(random.skewed(2 * minute, 14 * minute));
        ask(random.pick(place.changes));
        act(null, [tools.read(otherCode)]);
        act(null, [tools.edit(otherCode)]);
        act(null, [tools.shell(place.testCommand, place.passOutput)]);
        answer(`Changed ${otherCode}. The tests still pass. I did not commit this one yet.`);
      }
    },

    spiral: () => {
      title = `Fix ${failing.name} on CI`;
      ask(`the ${failing.name} test fails on CI but passes here`);
      useSkill('diagnosing-bugs', 'claude-proactive');
      act(null, [tools.shell(failing.command, failing.output, false)]);
      act(null, [tools.read(code), tools.read(test)]);
      const loops = random.whole(9, 17);
      for (let loop = 1; loop <= loops; loop += 1) {
        act(random.chance(0.3) ? 'That edit did not change the result. Reading the test again.' : null, [tools.edit(code)]);
        act(null, [tools.shell(failing.command, failing.output, false, random.skewed(9000, 16000))]);
        if (!scripted && loop % 5 === 0) {
          answer(`Still failing, with the same assertion. My edits to ${code} have not changed the count, so the bug is probably not in the loop. Next I want to check how the test builds its dates.`);
          pause(random.skewed(70 * second, 6 * minute));
          ask(random.pick(['still failing', "that didn't fix it. look at the timezone", 'stop editing and tell me what you think is wrong', 'ok try that']));
        }
      }
      act('Found it. The test machine runs in UTC and the fixture builds days in local time.', [tools.edit(test)]);
      act(null, [tools.shell(failing.command, place.passOutput)]);
      answer(
        `Found it. The test builds its days in local time, and CI runs in UTC. East of UTC the first day moves back one, so the store looked like it stopped early.\n\nI changed the fixture to build days in UTC. The store code was fine, so I put back my ${loops} edits to ${code}. The test passes here and with TZ=UTC.`,
      );
    },

    research: () => {
      const topic = random.pick(place.research);
      title = `Research ${topic}`;
      ask(`/research ${topic}`, 'research');
      typed('research');
      act('Splitting this into three questions.', [tools.read(random.pick(place.docs))]);
      delegate(
        'Three agents, one question each.',
        ['the query API', 'the container setup', 'retention'].map((part) => ({
          type: 'general-purpose',
          description: `Research ${part}`,
          calls: random.whole(8, 20),
          work: () => (random.chance(0.4) ? [tools.search(`${topic} ${part}`)] : [tools.fetch(`https://grafana.com/docs/tempo/latest/${part.replaceAll(' ', '-')}/`, part)]),
          report: `On ${part}: two primary sources agree. The details and links are in the notes.`,
        })),
        true,
      );
      act(null, [tools.write(`docs/research/${topic.split(' ').slice(0, 3).join('-')}.md`, `# ${topic}\n\n...`)]);
      act(null, [tools.edit(`docs/research/${topic.split(' ').slice(0, 3).join('-')}.md`)]);
      answer(`The notes are in docs/research. In short: search by the span attribute with TraceQL, then read each trace by its id. Retention is set per tenant.`);
    },

    day: () => {
      title = 'Session views: who reads them and what they decide';
      const turns = random.whole(14, 30);
      const once = new Set<string>();
      for (let turn = 0; turn < turns; turn += 1) {
        if (turn > 0) {
          pause(random.chance(0.14) ? random.between(25 * minute, 2 * hour) : random.skewed(2 * minute, 11 * minute));
        }
        const kind = random.weighted({ question: 40, change: 28, grill: once.has('grill') ? 0 : 10, glossary: once.has('glossary') ? 0 : 8, spec: once.has('spec') ? 0 : 7, fetch: 7 });
        once.add(kind);

        if (kind === 'question') {
          ask(random.pick(place.questions));
          act(null, [tools.grep(random.pick(place.patterns))]);
          answer(`It is in ${code}. It reads the value once, when the app starts.`);
        } else if (kind === 'change') {
          ask(random.pick(place.changes));
          act(null, [tools.read(code), tools.read(otherCode), tools.read(random.pick(place.docs))]);
          for (let edit = random.whole(1, 4); edit > 0; edit -= 1) {
            act(null, [tools.edit(random.chance(0.7) ? code : otherCode)]);
          }
          act(null, [tools.shell(place.testCommand, place.passOutput)]);
          answer(`Done. ${code} changed and the tests pass.`);
        } else if (kind === 'grill') {
          ask('grill me on who reads a session view');
          useSkill('grilling', 'claude-proactive');
          answer('First question. Who opens a session view: the skill author after their skill fired, or the developer who ran the session? My guess is the skill author, because Studio exists to watch skills.');
          for (let reply = random.whole(3, 6); reply > 0; reply -= 1) {
            pause(random.skewed(50 * second, 3 * minute));
            ask(random.pick(['the skill author mostly', 'both, but start with the author', 'from Home, a skill tile', 'no, by repo first then by person']));
            answer('Next question. When they land on the session, what do they look for first: where the time went, or what failed?');
          }
        } else if (kind === 'glossary') {
          ask('add Session, Prompt and Tool call to CONTEXT.md');
          useSkill('domain-modeling', 'claude-proactive');
          act(null, [tools.read('CONTEXT.md')]);
          act(null, [tools.edit('CONTEXT.md')]);
          act(null, [tools.edit('CONTEXT.md')]);
          answer('Added three terms under Measurement. Session is one run of claude. Prompt is one thing the developer sent. Tool call is one step Claude asked a tool to do.');
        } else if (kind === 'spec') {
          ask('/to-spec', 'to-spec');
          typed('to-spec');
          act(null, [tools.read('docs/agents/issue-tracker.md')]);
          act(null, [tools.shell('gh issue create --title "Session view" --body-file spec.md', 'https://github.com/malcolm/skillworks/issues/70')]);
          useSkill('to-tickets', 'nested-skill');
          for (let ticket = random.whole(3, 5); ticket > 0; ticket -= 1) {
            act(null, [tools.shell(`gh issue create --title "Session view ticket ${ticket}"`, `https://github.com/malcolm/skillworks/issues/${70 + ticket}`)]);
          }
          answer('The spec is issue 70. It has 4 tickets as sub-issues, each with its blocking edges.');
        } else {
          ask('what do the Loki docs say about tail?');
          const call = callModel(main, clock, null, 'tool_use', 1);
          clock = runTools(main, call, [tools.fetch('https://grafana.com/docs/loki/latest/reference/loki-http-api/', 'tail')], call.at);
          sideCall('web_fetch_apply', clock - 2500, haiku, null, random.whole(3000, 9000));
          answer('Loki streams new lines over a WebSocket at /loki/api/v1/tail. It takes a query, a start and a limit.');
        }
      }
    },

    scripted: () => {
      title = null;
      const tickets = random.whole(1, 3);
      const loop = tickets > 1 ? 'spec-loop' : 'implement';
      ask(`/${loop} ${issue.ref}`, loop);
      typed(loop);
      for (let ticket = 0; ticket < tickets; ticket += 1) {
        if (tickets > 1) {
          useSkill('implement', 'nested-skill');
        }
        act(null, [tools.shell(place.issueCommand(issue.ref), `${issue.ref} ${issue.title} [open]`)]);
        act(null, [tools.read(code), tools.read(test)]);
        useSkill('tdd', 'nested-skill');
        for (let cycle = random.whole(2, 5); cycle > 0; cycle -= 1) {
          testCycle(random.chance(0.4));
        }
        useSkill('code-review', 'nested-skill');
        delegate('Reviewing before the commit.', ['Standards', 'Spec'].map(reviewTask), false);
        act(null, [tools.shell(`git commit -m "${issue.title}"`, `[main ${random.hex(7)}] ${issue.title}`)]);
      }
      answer(`${tickets} ticket${tickets > 1 ? 's are' : ' is'} done and committed. Tests pass.`);
    },
  };

  shapes[shape]();

  // Words the model wrote for the title follow the responses switch like any other reply.
  const titleStep = steps.find((step) => step.kind === 'model' && step.purpose === 'generate_session_title');
  if (titleStep?.kind === 'model' && title !== null) {
    titleStep.said = said(place.switches.responses, title);
  }

  const ordered = steps.toSorted((a, b) => a.at - b.at);

  for (const step of ordered) {
    if (step.kind !== 'prompt') continue;
    prompts.push({ index: step.prompt, stepId: step.id, startMs: step.at, endMs: step.at });
  }
  for (const step of ordered) {
    const span = prompts[step.prompt];
    if (!span) continue;
    span.startMs = Math.min(span.startMs, step.at - step.ms);
    span.endMs = Math.max(span.endMs, step.at);
  }

  const startAt = Math.min(...ordered.map((step) => step.at - step.ms));
  const endAt = Math.max(...ordered.map((step) => step.at));

  return {
    id: `${random.hex(8)}-${random.hex(4)}-4${random.hex(3)}-${random.pick(['8', '9', 'a', 'b'])}${random.hex(3)}-${random.hex(12)}`,
    repository: place.repository,
    person: person.handle,
    startMs: startAt,
    endMs: endAt,
    running: false,
    entry: scripted ? 'scripted' : 'interactive',
    version: random.pick(['2.1.268', '2.1.269', '2.1.269', '2.1.270']),
    terminal: person.terminal,
    title: title === null ? null : place.switches.responses ? title : null,
    switches: place.switches,
    contextLimit: 1_000_000,
    prompts,
    steps: ordered,
  };
}

// Cut at now, so the newest session reads as one still running.
function cutAt(session: Session, now: number): Session {
  const steps = session.steps.filter((step) => step.at <= now);
  const prompts = session.prompts
    .filter((span) => span.startMs <= now)
    .map((span) => ({ ...span, endMs: Math.max(span.startMs, ...steps.filter((step) => step.prompt === span.index).map((step) => step.at)) }));

  return { ...session, steps, prompts, endMs: Math.max(...steps.map((step) => step.at)), running: steps.length < session.steps.length };
}

export function fortnight(now: number): Session[] {
  const random = randomFrom(20260915);
  const sessions: Session[] = [];
  const today = Math.floor(now / day) * day;

  for (let back = 13; back >= 0; back -= 1) {
    const date = today - back * day;
    const weekday = new Date(date).getUTCDay();
    const weekend = weekday === 0 || weekday === 6;

    for (const person of people) {
      const expected = person.perDay * (weekend ? (person.scripted ? 0.5 : 0.15) : 1);
      let count = Math.floor(expected) + (random.chance(expected % 1) ? 1 : 0);

      while (count > 0) {
        count -= 1;
        const place = places[random.weighted(person.places)];
        const shape: Shape = person.scripted ? 'scripted' : random.weighted({ quick: 30, feature: 22, day: back === 0 ? 0 : 10, spiral: 14, research: place.research.length > 0 ? 8 : 0 });
        const startMs = date + random.between(7.5, 17.5) * hour;
        const seed = Math.floor(random.next() * 2 ** 31);

        if (startMs > now - 2 * minute) continue;

        const session = buildSession(randomFrom(seed), place, person, startMs, shape);
        if (session.endMs <= now) sessions.push(session);
      }
    }
  }

  const live = buildSession(randomFrom(915), places.skillworks, people[0], now - 14 * minute, 'feature');
  sessions.push(cutAt(live, now - 20 * second));

  return sessions.toSorted((a, b) => b.startMs - a.startMs);
}
