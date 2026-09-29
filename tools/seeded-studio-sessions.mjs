// Scripted rather than random, so each Bar is crossed on purpose and the seeded month keeps its random numbers.

import { randomBytes, randomUUID } from 'node:crypto';

const opus = 'claude-opus-5';
const sonnet = 'claude-sonnet-5';
const haiku = 'claude-haiku-4-5-20251001';

// Claude Code states a window only through this marker on the model id.
const windowMarker = '[1m]';
const million = (model) => `${model}${windowMarker}`;

const hourMs = 60 * 60 * 1000;
const hex = (bytes) => randomBytes(bytes).toString('hex');
const toolUseId = () => `toolu_${hex(12)}`;

class Run {
  events = [];
  spans = [];
  context = 0;
  skill = undefined;
  agent = undefined;
  parent = undefined;
  interaction = undefined;
  request = undefined;
  // Turns before the first Prompt still need a trace to sit in.
  trace = hex(16);

  constructor(startMs, repository, model, price) {
    this.session = { id: randomUUID(), sequence: 0 };
    this.at = startMs;
    this.model = model;
    this.price = price;
    const [owner, name] = repository.split('/');
    this.place = { 'vcs.owner.name': owner, 'vcs.repository.name': name };
  }

  pass(ms) {
    this.at += ms;
  }

  event(name, attributes) {
    this.events.push({ at: this.at, session: this.session, name, attributes: { ...this.place, ...attributes } });
  }

  span(name, from, until, attributes, parent = this.parent) {
    const span = {
      traceId: this.trace,
      spanId: hex(8),
      parent,
      name,
      from,
      until,
      attributes: { 'session.id': this.session.id, agent_id: this.agent, ...attributes },
    };
    this.spans.push(span);
    return span;
  }

  titled(words) {
    this.event('assistant_response', { response: words, query_source: 'generate_session_title', model: haiku });
    this.pass(300);
  }

  prompt(words) {
    this.trace = hex(16);
    this.parent = undefined;
    this.interaction = this.span('claude_code.interaction', this.at, this.at, {});
    this.parent = this.interaction.spanId;
    this.event('user_prompt', { prompt: words, prompt_length: String(words.length) });
    this.pass(400);
  }

  activate(skill, trigger, source = 'projectSettings') {
    this.event('skill_activated', { 'skill.name': skill, invocation_trigger: trigger, 'skill.source': source });
    this.skill = skill;
    this.pass(200);
  }

  turn({ read = this.context, written = 3000, output = 900, ms = 4500, source = 'main', model = this.model } = {}) {
    const from = this.at;
    const input = 40;
    const price = this.price[model.replace(windowMarker, '')];
    const cost = (input * price.input + output * price.output + read * price.cacheRead + written * price.cacheCreation) / 1e6;
    this.request = `req_${hex(12)}`;
    this.context = read + written;
    this.pass(ms);

    this.event('api_request', {
      model,
      'skill.name': this.skill,
      effort: 'xhigh',
      cost_usd: cost.toFixed(6),
      input_tokens: String(input),
      output_tokens: String(output),
      cache_read_tokens: String(read),
      cache_creation_tokens: String(written),
      request_id: this.request,
      duration_ms: String(ms),
      speed: 'normal',
      // A Subagent's Turns are told apart by their Spans, and a source other than main would read as a side request.
      query_source: this.agent ? undefined : source,
    });
    this.span('claude_code.llm_request', from, this.at, { request_id: this.request, model });
    this.pass(150);
  }

  rateLimited(ms = 1200) {
    this.pass(ms);
    this.event('api_error', { model: this.model, error_type: 'rate_limit_error', status_code: '429', duration_ms: String(ms) });
    this.pass(2000);
  }

  answer(words) {
    this.event('assistant_response', { response: words, response_length: String(words.length), request_id: this.request });
    if (!this.agent && this.interaction) {
      this.interaction.until = this.at;
    }
    this.pass(200);
  }

  // The wait for a person and the hook both run inside the length Claude Code records for the call.
  tool(name, input, { ms = 1500, fault, wait = 0, hook = 0 } = {}) {
    const use = toolUseId();
    const from = this.at;
    const call = this.span('claude_code.tool', from, from, { tool_use_id: use, tool_name: name });

    if (wait > 0) {
      this.span('claude_code.tool.blocked_on_user', this.at, this.at + wait, { tool_use_id: use }, call.spanId);
      this.pass(wait);
    }
    this.event('tool_decision', { tool_name: name, decision: 'accept', source: wait > 0 ? 'user_temporary' : 'config', tool_use_id: use });

    if (hook > 0) {
      this.span('claude_code.hook', this.at, this.at + hook, { hook_event: 'PreToolUse' }, call.spanId);
      this.pass(hook);
    }
    this.span('claude_code.tool.execution', this.at, this.at + ms, { tool_use_id: use }, call.spanId);
    this.pass(ms);
    call.until = this.at;

    this.event('tool_result', {
      tool_name: name,
      success: fault ? 'false' : 'true',
      error_type: fault,
      source: wait > 0 ? 'user_temporary' : 'config',
      tool_input: JSON.stringify(input),
      tool_use_id: use,
      duration_ms: String(this.at - from),
    });
    this.pass(300);
  }

  refused(name, input, wait) {
    const use = toolUseId();
    const call = this.span('claude_code.tool', this.at, this.at + wait, { tool_use_id: use, tool_name: name });
    this.span('claude_code.tool.blocked_on_user', this.at, this.at + wait, { tool_use_id: use }, call.spanId);
    this.pass(wait);
    this.event('tool_decision', { tool_name: name, decision: 'reject', source: 'user_reject', tool_use_id: use, tool_input: JSON.stringify(input) });
    this.pass(300);
  }

  hookBlocked(name, input, hook = 900) {
    const use = toolUseId();
    const call = this.span('claude_code.tool', this.at, this.at + hook, { tool_use_id: use, tool_name: name });
    this.span('claude_code.hook', this.at, this.at + hook, { hook_event: 'PreToolUse' }, call.spanId);
    this.pass(hook);
    this.event('tool_decision', { tool_name: name, decision: 'reject', source: 'hook', tool_use_id: use, tool_input: JSON.stringify(input) });
    this.pass(300);
  }

  // Only the Span that wraps the whole Subagent carries both its agent id and the id of the call that started it.
  subagent(description, type, brief, model, work) {
    const use = toolUseId();
    const from = this.at;
    const call = this.span('claude_code.tool', from, from, { tool_use_id: use, tool_name: 'Agent' });
    const caller = { parent: this.parent, context: this.context, request: this.request, skill: this.skill, model: this.model };

    this.pass(50);
    this.agent = `a${hex(8)}`;
    const wrap = this.span('claude_code.tool.execution', this.at, this.at, { tool_use_id: use }, call.spanId);
    Object.assign(this, { parent: wrap.spanId, context: 14000, skill: undefined, model });

    work(this);

    wrap.until = this.at;
    this.agent = undefined;
    Object.assign(this, caller);
    this.pass(50);
    call.until = this.at;

    this.event('tool_result', {
      tool_name: 'Agent',
      success: 'true',
      source: 'config',
      tool_input: JSON.stringify({ description, subagent_type: type, prompt: brief }),
      tool_use_id: use,
      duration_ms: String(this.at - from),
    });
    this.pass(300);
  }
}

// Crosses every Part of the Time breakdown, every Friction and Fault, a far dearer Subagent and a stated window.
function tour(startMs, price) {
  const run = new Run(startMs, 'malcolm/skillworks', million(opus), price);

  run.titled('Add a retry to the Loki reader');
  run.prompt('The Loki reader gives up on the first 503. Add a retry with a Patience, and cover it with a test.');
  run.turn({ read: 22000, written: 26000, output: 400 });
  run.activate('implement', 'claude-proactive');
  run.turn({ output: 1200 });
  run.tool('Read', { file_path: 'src/Skillworks.Core/Shared/Stores/EventsStore/EventsStoreReader.cs' }, { ms: 300 });
  run.tool('Grep', { pattern: 'Patience', path: 'src' }, { ms: 700 });
  run.turn({ output: 700 });

  run.subagent('Find every reader', 'Explore', 'List every class that reads a store and how it waits.', haiku, (agent) => {
    agent.turn({ written: 9000, output: 500, ms: 2500 });
    agent.tool('Grep', { pattern: 'StoreReader', path: 'src' }, { ms: 600 });
    agent.turn({ output: 900, ms: 3000 });
    agent.answer('Three readers wait on a store: EventsStoreReader, TraceStoreReader and CollectorReader.');
  });
  run.subagent('Read the tests', 'Explore', 'Read the reader tests and say which cover a failed read.', haiku, (agent) => {
    agent.turn({ written: 8000, output: 400, ms: 2200 });
    agent.tool('Glob', { pattern: 'tests/**/*Reader*.cs' }, { ms: 400 });
    agent.turn({ output: 800, ms: 2600 });
    agent.answer('Two tests cover a failed read, and neither covers a 503.');
  });
  run.subagent('Draft the retry', 'general-purpose', 'Write a retry for EventsStoreReader and its tests.', opus, (agent) => {
    for (let pass = 0; pass < 9; pass++) {
      agent.turn({ written: 12000, output: 4200, ms: 9000 });
      agent.tool(pass % 3 === 0 ? 'Read' : 'Edit', { file_path: `src/Skillworks.Core/Shared/Stores/EventsStore/Retry${pass % 2}.cs` }, { ms: 500, hook: 400 });
    }
    agent.tool('Bash', { command: 'dotnet build' }, { ms: 14000, fault: 'ShellError' });
    agent.turn({ written: 6000, output: 3000, ms: 7000 });
    agent.answer('The retry is drafted, and the build fails on a missing using.');
  });

  run.turn({ output: 1400 });
  run.tool('Edit', { file_path: 'src/Skillworks.Core/Shared/Stores/EventsStore/EventsStoreReader.cs' }, { ms: 600, hook: 1800 });
  run.rateLimited();
  run.turn({ output: 600 });
  run.hookBlocked('Bash', { command: 'git push --force' });
  run.turn({ output: 500 });
  run.tool('Bash', { command: 'dotnet test tests/Skillworks.Core.Tests' }, { ms: 42000, wait: 150000, hook: 1500 });
  run.turn({ output: 900 });
  run.answer('The reader now retries a 503 until its Patience runs out, and a test proves it.');

  run.pass(4 * 60 * 1000);
  run.prompt('Now tidy the comments on that change.');
  run.activate('comment-sweep', 'user-slash');
  run.turn({ output: 800 });
  run.tool('Bash', { command: 'git diff' }, { ms: 900 });
  run.turn({ output: 1100 });
  run.refused('Bash', { command: 'git commit -am "tidy"' }, 9000);
  run.skill = 'third-party';
  run.turn({ output: 600, model: million(opus) });
  run.turn({ output: 300, source: 'compact', written: 5000 });
  run.skill = 'comment-sweep';
  run.turn({ output: 700 });
  run.answer('Two comments cut, one kept. I left the commit to you.');

  return run;
}

// Crosses the Bars a stuck loop trips, with no model that states its window.
function stuck(startMs, price) {
  const run = new Run(startMs, 'acme/billing-api', opus, price);

  run.titled('Fix the failing invoice test');
  run.prompt('npm test fails on the invoice rounding. Make it pass.');
  run.activate('diagnosing-bugs', 'claude-proactive');
  run.turn({ read: 18000, written: 24000, output: 800 });
  run.tool('Read', { file_path: 'src/billing/invoice.ts' }, { ms: 250, hook: 900 });

  for (let attempt = 0; attempt < 6; attempt++) {
    run.turn({ output: 1300 });
    run.tool('Edit', { file_path: 'src/billing/invoice.ts', old_string: 'Math.round', new_string: `Math.round${attempt}` }, { ms: 700, hook: 5200 });
    if (attempt < 4) {
      run.turn({ output: 400 });
      run.tool('Bash', { command: 'npm test' }, { ms: 8000, fault: 'ShellError', hook: 3100 });
    }
  }

  run.hookBlocked('Bash', { command: 'rm -rf node_modules' }, 2500);
  run.pass(7 * 60 * 1000);
  run.turn({ read: 1500, written: 64000, output: 900 });
  run.tool('Bash', { command: 'npm test -- invoice' }, { ms: 9000, hook: 3100 });
  run.turn({ output: 600 });
  run.answer('It passes now: the rounding used banker\'s rounding where the tests expect half up.');

  return run;
}

// A research run on a model with a million-token window, read until the context is nearly full.
function full(startMs, price) {
  const run = new Run(startMs, 'malcolm/podium', million(sonnet), price);

  run.titled('Survey the scheduling papers');
  run.prompt('Read every paper in docs/papers and write a summary of how each one schedules work.');
  run.activate('research', 'user-slash');
  run.turn({ read: 30000, written: 40000, output: 600 });

  for (let paper = 1; paper <= 13; paper++) {
    run.tool('Read', { file_path: `docs/papers/paper-${paper}.pdf` }, { ms: 1800 });
    run.turn({ written: 60000, output: 700, ms: 7000 });
  }

  run.tool('Write', { file_path: 'docs/papers/summary.md' }, { ms: 400 });
  run.turn({ written: 4000, output: 5200, ms: 30000 });
  run.answer('The summary is in docs/papers/summary.md. Nine papers schedule by deadline, four by priority.');

  return run;
}

// A quiet run with no skill in force, and Turns before the first Prompt.
function quiet(startMs, price) {
  const run = new Run(startMs, 'malcolm/podium', sonnet, price);

  run.turn({ read: 0, written: 16000, output: 200, ms: 2500 });
  run.skill = 'third-party';
  run.turn({ output: 300, ms: 2000 });
  run.skill = undefined;
  run.titled('Rename the podium config');
  run.prompt('Rename podium.json to podium.config.json and fix every reference.');
  run.turn({ output: 600 });
  run.tool('Grep', { pattern: 'podium.json' }, { ms: 500 });
  run.turn({ output: 500 });
  run.tool('Bash', { command: 'git mv podium.json podium.config.json' }, { ms: 300, wait: 12000 });
  run.turn({ output: 700 });
  run.tool('Edit', { file_path: 'src/config.ts' }, { ms: 400 });
  run.turn({ output: 300 });
  run.answer('Renamed, and the one reference in src/config.ts now points at the new name.');

  run.pass(3 * 60 * 1000);
  run.prompt('Thanks. Anything else that reads it?');
  run.turn({ output: 250 });
  run.answer('No. Nothing else reads it.');

  return run;
}

// A clean review with one skill calling another, so the Findings read as nothing crossed.
function review(startMs, price) {
  const run = new Run(startMs, 'malcolm/skillworks', opus, price);

  run.titled('Review the retry change');
  run.prompt('/review-changes since main');
  run.activate('review-changes', 'user-slash');
  run.turn({ read: 20000, written: 22000, output: 900 });
  run.tool('Bash', { command: 'git diff main' }, { ms: 800 });
  run.turn({ output: 2200 });
  run.activate('comment-sweep', 'nested-skill');
  run.turn({ output: 700 });
  run.tool('Read', { file_path: 'src/Skillworks.Core/Shared/Stores/EventsStore/EventsStoreReader.cs' }, { ms: 300 });
  run.turn({ output: 500 });
  run.skill = 'review-changes';
  run.turn({ output: 1800 });
  run.answer('No findings. The retry reads its Patience from the Clock, and the tests cover a 503.');

  run.pass(2 * 60 * 1000);
  run.prompt('Unslop the commit message.');
  run.activate('unslop', 'claude-proactive');
  run.turn({ output: 300, model: haiku });
  run.answer('The Loki reader retries a 503 until its Patience runs out.');

  return run;
}

// All inside a week of the push: the Trace store finds a span only when the search window holds it and its arrival.
export function wholeSessions(now, price) {
  const runs = [tour, stuck, full, quiet, review].map((write, place) => write(now - (6 - place) * hourMs, price));

  return {
    sessions: runs.map((run) => run.session.id),
    events: runs.flatMap((run) => run.events),
    spans: runs.flatMap((run) => run.spans),
  };
}

export function otlpSpan(span) {
  return {
    traceId: span.traceId,
    spanId: span.spanId,
    ...(span.parent === undefined ? {} : { parentSpanId: span.parent }),
    name: span.name,
    kind: 1,
    startTimeUnixNano: `${BigInt(Math.round(span.from)) * 1000000n}`,
    endTimeUnixNano: `${BigInt(Math.round(span.until)) * 1000000n}`,
    attributes: Object.entries(span.attributes)
      .filter(([, value]) => value !== undefined)
      .map(([key, value]) => ({ key, value: { stringValue: value } })),
  };
}
