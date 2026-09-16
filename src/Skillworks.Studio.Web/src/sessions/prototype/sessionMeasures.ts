// PROTOTYPE — throwaway. What every variant reads off a session. The variants disagree about how to show these,
// not about what they are, so the numbers agree when you flip between them.

import type {
  ModelStep,
  PromptSpan,
  PromptStep,
  Said,
  Session,
  SessionStep,
  SkillStep,
  SubagentStep,
  ToolStep,
} from './sessionModel';

const second = 1000;
const minute = 60 * second;
const hour = 60 * minute;
const day = 24 * hour;

// ---- words and numbers ----

export const format = {
  usd: (value: number) =>
    value >= 100 ? `$${value.toFixed(0)}` : value >= 1 ? `$${value.toFixed(2)}` : value >= 0.01 ? `$${value.toFixed(3)}` : `$${value.toFixed(4)}`,
  int: (value: number) => Math.round(value).toLocaleString('en-GB'),
  tokens: (value: number) => (value >= 1e6 ? `${(value / 1e6).toFixed(1)}M` : value >= 1e3 ? `${Math.round(value / 1e3)}k` : String(Math.round(value))),
  bytes: (value: number) => (value >= 1024 ? `${(value / 1024).toFixed(1)} KB` : `${value} B`),
  percent: (share: number) => `${Math.round(share * 100)}%`,
  duration: (ms: number) => {
    if (ms < second) return `${Math.round(ms)} ms`;
    const seconds = ms / second;
    if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)} s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ${String(Math.floor(seconds % 60)).padStart(2, '0')}s`;
    return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`;
  },
  short: (ms: number) =>
    ms < minute ? `${Math.round(ms / second)}s` : ms < hour ? `${Math.round(ms / minute)}m` : `${(ms / hour).toFixed(1).replace('.0', '')}h`,
  clock: (ms: number, seconds = false) =>
    new Date(ms).toLocaleTimeString('en-GB', seconds ? { hour: '2-digit', minute: '2-digit', second: '2-digit' } : { hour: '2-digit', minute: '2-digit' }),
  day: (ms: number) => new Date(ms).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }),
  ago: (ms: number, now: number) => {
    const past = now - ms;
    if (past < minute) return 'just now';
    if (past < hour) return `${Math.round(past / minute)}m ago`;
    if (past < day) return `${Math.round(past / hour)}h ago`;
    return `${Math.round(past / day)}d ago`;
  },
  model: (model: string) => model.replace('claude-', '').replace(/-\d{8}$/, '').replace('[1m]', ' 1M'),
  trigger: (trigger: string) =>
    ({ 'user-slash': 'typed', 'claude-proactive': 'Claude chose it', 'nested-skill': 'another skill called it', 'agent-preload': 'agent preload' })[trigger] ?? trigger,
};

export const startOf = (step: SessionStep) => step.at - step.ms;

export const noRepository = '~none';

export const repositoryLabel = (repository: string) => (repository === '' ? 'No repository' : repository);

// ---- lanes ----

export type Lane = 'prompt' | 'skill' | 'main' | 'other' | 'subagent' | 'shell' | 'edit' | 'read' | 'tool' | 'hook' | 'fault';

export const lanes: { key: Lane; label: string }[] = [
  { key: 'prompt', label: 'Prompts' },
  { key: 'skill', label: 'Skills' },
  { key: 'main', label: 'Model · main' },
  { key: 'other', label: 'Model · other' },
  { key: 'subagent', label: 'Subagents' },
  { key: 'shell', label: 'Shell' },
  { key: 'edit', label: 'Edit & write' },
  { key: 'read', label: 'Read & search' },
  { key: 'tool', label: 'Other tools' },
  { key: 'hook', label: 'Hooks' },
  { key: 'fault', label: 'Faults' },
];

// A failed step sits in its own lane and in Faults too, so the Faults lane alone answers "what went wrong".
export function lanesOf(step: SessionStep): Lane[] {
  switch (step.kind) {
    case 'prompt':
      return ['prompt'];
    case 'skill':
      return ['skill'];
    case 'model':
      return [step.thread === 'main' ? 'main' : 'other'];
    case 'modelError':
      return ['fault'];
    case 'subagent':
      return ['subagent'];
    case 'hook':
      return step.blocking > 0 || step.errors > 0 ? ['hook', 'fault'] : ['hook'];
    case 'rejected':
      return ['fault'];
    case 'tool': {
      const lane: Lane = step.family === 'shell' || step.family === 'edit' || step.family === 'read' ? step.family : step.family === 'agent' ? 'subagent' : 'tool';
      // The Agent tool only launches the subagent, whose own bar already covers the work.
      const own: Lane[] = step.family === 'agent' ? [] : [lane];
      return step.ok ? own : [...own, 'fault'];
    }
  }
}

// ---- browsing ----

export interface RepositoryRow {
  repository: string;
  sessions: number;
  people: string[];
  lastMs: number;
  costUsd: number;
  running: number;
}

export const costOf = (session: Session) => session.steps.reduce((sum, step) => sum + (step.kind === 'model' ? step.costUsd : 0), 0);

export function repositories(sessions: Session[]): RepositoryRow[] {
  const rows = new Map<string, RepositoryRow>();

  for (const session of sessions) {
    const row = rows.get(session.repository) ?? { repository: session.repository, sessions: 0, people: [], lastMs: 0, costUsd: 0, running: 0 };
    row.sessions += 1;
    row.lastMs = Math.max(row.lastMs, session.endMs);
    row.costUsd += costOf(session);
    row.running += session.running ? 1 : 0;
    if (!row.people.includes(session.person)) row.people.push(session.person);
    rows.set(session.repository, row);
  }

  return [...rows.values()].toSorted((a, b) => b.lastMs - a.lastMs);
}

export interface PersonRow {
  person: string;
  sessions: Session[];
  lastMs: number;
  costUsd: number;
}

export function peopleIn(sessions: Session[], repository: string): PersonRow[] {
  const rows = new Map<string, PersonRow>();

  for (const session of sessions.filter((each) => each.repository === repository)) {
    const row = rows.get(session.person) ?? { person: session.person, sessions: [], lastMs: 0, costUsd: 0 };
    row.sessions.push(session);
    row.lastMs = Math.max(row.lastMs, session.endMs);
    row.costUsd += costOf(session);
    rows.set(session.person, row);
  }

  return [...rows.values()].toSorted((a, b) => b.lastMs - a.lastMs);
}

export interface DayRow {
  dayMs: number;
  label: string;
  sessions: Session[];
}

export function daysOf(sessions: Session[], now: number): DayRow[] {
  const today = Math.floor(now / day) * day;
  const rows = new Map<number, DayRow>();

  for (const session of [...sessions].toSorted((a, b) => b.startMs - a.startMs)) {
    const dayMs = Math.floor(session.startMs / day) * day;
    const label = dayMs === today ? 'Today' : dayMs === today - day ? 'Yesterday' : format.day(dayMs);
    const row = rows.get(dayMs) ?? { dayMs, label, sessions: [] };
    row.sessions.push(session);
    rows.set(dayMs, row);
  }

  return [...rows.values()].toSorted((a, b) => b.dayMs - a.dayMs);
}

export function sessionName(session: Session): string {
  if (session.title !== null) return session.title;

  const first = session.steps.find((step): step is PromptStep => step.kind === 'prompt');
  if (first?.command) return `/${first.command}`;
  if (first?.said.text) return first.said.text;

  const skills = [...new Set(session.steps.filter((step): step is SkillStep => step.kind === 'skill').map((step) => step.skill))];
  if (skills.length > 0) return skills.join(' + ');

  const tools = [...new Set(session.steps.filter((step): step is ToolStep => step.kind === 'tool').map((step) => step.tool))].slice(0, 3);
  return `Words withheld · ${session.prompts.length} prompt${session.prompts.length === 1 ? '' : 's'}${tools.length > 0 ? ` · ${tools.join(', ')}` : ''}`;
}

// ---- the summary ----

export interface SessionSummary {
  wallMs: number;
  busyMs: number;
  costUsd: number;
  prompts: number;
  mainCalls: number;
  otherCalls: number;
  subagents: number;
  toolCalls: number;
  failedTools: number;
  apiErrors: number;
  rejected: number;
  hookMs: number;
  skills: SkillStep[];
  peakContext: number;
  cacheRebuilds: number;
  models: { model: string; calls: number; costUsd: number }[];
}

export const inRange = (step: SessionStep, range: [number, number] | null) => range === null || (step.at >= range[0] && startOf(step) <= range[1]);

export function summarize(session: Session, range: [number, number] | null = null): SessionSummary {
  const steps = session.steps.filter((step) => inRange(step, range));
  const models = new Map<string, { model: string; calls: number; costUsd: number }>();
  const context = contextSeries(session).filter((point) => inRange(point.step, range));
  const summary: SessionSummary = {
    wallMs: 0,
    busyMs: 0,
    costUsd: 0,
    prompts: 0,
    mainCalls: 0,
    otherCalls: 0,
    subagents: 0,
    toolCalls: 0,
    failedTools: 0,
    apiErrors: 0,
    rejected: 0,
    hookMs: 0,
    skills: [],
    peakContext: Math.max(0, ...context.map((point) => point.context)),
    cacheRebuilds: context.filter((point) => point.rebuilt).length,
    models: [],
  };

  for (const step of steps) {
    switch (step.kind) {
      case 'prompt':
        summary.prompts += 1;
        break;
      case 'model': {
        summary.costUsd += step.costUsd;
        if (step.thread === 'main') summary.mainCalls += 1;
        else summary.otherCalls += 1;
        const row = models.get(step.model) ?? { model: step.model, calls: 0, costUsd: 0 };
        row.calls += 1;
        row.costUsd += step.costUsd;
        models.set(step.model, row);
        break;
      }
      case 'modelError':
        summary.apiErrors += 1;
        break;
      case 'tool':
        summary.toolCalls += 1;
        if (!step.ok) summary.failedTools += 1;
        break;
      case 'rejected':
        summary.rejected += 1;
        break;
      case 'hook':
        summary.hookMs += step.ms;
        break;
      case 'subagent':
        summary.subagents += 1;
        break;
      case 'skill':
        summary.skills.push(step);
        break;
    }
  }

  const [from, to] = range ?? [session.startMs, session.endMs];
  const split = timeSplit(session, range);
  summary.wallMs = to - from;
  summary.busyMs = summary.wallMs - split.parts.filter((part) => part.key === 'yourTurn' || part.key === 'quiet').reduce((sum, part) => sum + part.ms, 0);
  summary.models = [...models.values()].toSorted((a, b) => b.costUsd - a.costUsd);

  return summary;
}

// ---- where the time went ----

export type TimeKey = 'waiting' | 'tool' | 'hook' | 'model' | 'subagent' | 'side' | 'quiet' | 'yourTurn';

export interface TimePart {
  key: TimeKey;
  label: string;
  ms: number;
  note: string;
}

export interface TimeKind {
  key: string;
  label: string;
  ms: number;
}

const timeParts: { key: TimeKey; label: string; note: string }[] = [
  { key: 'waiting', label: 'Waiting for your OK', note: 'A tool was ready to run and waited for a developer to allow it.' },
  { key: 'tool', label: 'Tools running', note: 'Tools on the main thread, from the moment they were allowed to the moment they returned.' },
  { key: 'hook', label: 'Hooks', note: 'Hook scripts on the main thread, before or after a tool.' },
  { key: 'model', label: 'Model thinking', note: 'Main-thread model calls, from the request to the last token.' },
  { key: 'subagent', label: 'Only subagents working', note: 'The main thread had nothing running and waited on subagents.' },
  { key: 'side', label: 'Side requests', note: 'Only a side request ran, such as naming the session or compacting it.' },
  { key: 'quiet', label: 'Nothing running, mid-prompt', note: 'Inside a prompt, with no step running. Streaming and Claude Code itself.' },
  { key: 'yourTurn', label: 'Your turn', note: 'Between one prompt ending and the next starting: reading, thinking, typing, away.' },
];

// Each moment of the session is given to exactly one part, the first in the order above that was running, so the parts
// add up to the session's length and read as one bar.
export function timeSplit(session: Session, range: [number, number] | null = null): { parts: TimePart[]; kinds: TimeKind[] } {
  const [from, to] = range ?? [session.startMs, session.endMs];
  const intervals: { start: number; end: number; rank: number }[] = [];
  const rank = (key: TimeKey) => timeParts.findIndex((part) => part.key === key);
  const kinds = new Map<string, TimeKind>();
  const addKind = (key: string, label: string, ms: number) => {
    const row = kinds.get(key) ?? { key, label, ms: 0 };
    row.ms += ms;
    kinds.set(key, row);
  };

  for (const step of session.steps) {
    const start = Math.max(from, startOf(step));
    const end = Math.min(to, step.at);
    if (end <= start && step.ms > 0) continue;
    const share = step.ms > 0 ? (end - start) / step.ms : 0;

    if (step.kind === 'model') {
      const key: TimeKey = step.thread === 'main' ? 'model' : step.thread === 'side' ? 'side' : 'subagent';
      if (step.thread !== 'subagent') intervals.push({ start, end, rank: rank(key) });
      addKind(`model-${step.thread}`, step.thread === 'main' ? 'Model · main thread' : step.thread === 'side' ? 'Model · side requests' : 'Model · subagents', step.ms * share);
    } else if (step.kind === 'tool' && step.family !== 'agent') {
      const waitEnd = Math.min(end, Math.max(start, startOf(step) + step.waitedMs));
      if (step.agent === null) {
        if (step.waitedMs > 0) intervals.push({ start, end: waitEnd, rank: rank('waiting') });
        intervals.push({ start: waitEnd, end, rank: rank('tool') });
      }
      if (step.waitedMs > 0) addKind('waiting', 'Waiting for your OK', Math.max(0, waitEnd - start));
      const family = step.family === 'shell' ? 'Tools · shell' : step.family === 'edit' ? 'Tools · edit & write' : step.family === 'read' ? 'Tools · read & search' : 'Tools · other';
      addKind(`tool-${step.family}`, family, Math.max(0, end - waitEnd));
    } else if (step.kind === 'hook') {
      if (step.agent === null) intervals.push({ start, end, rank: rank('hook') });
      addKind('hook', 'Hooks', step.ms * share);
    } else if (step.kind === 'subagent') {
      intervals.push({ start, end, rank: rank('subagent') });
      addKind('subagent', 'Subagents, start to finish', step.ms * share);
    } else if (step.kind === 'rejected') {
      intervals.push({ start, end, rank: rank('waiting') });
      addKind('waiting', 'Waiting for your OK', step.ms * share);
    }
  }

  for (const span of session.prompts) {
    const start = Math.max(from, span.startMs);
    const end = Math.min(to, span.endMs);
    if (end > start) intervals.push({ start, end, rank: rank('quiet') });
  }
  intervals.push({ start: from, end: to, rank: rank('yourTurn') });

  const edges = [...new Set(intervals.flatMap((interval) => [interval.start, interval.end]))].toSorted((a, b) => a - b);
  const totals = Array.from({ length: timeParts.length }, () => 0);
  const byStart = [...intervals].toSorted((a, b) => a.start - b.start);
  let cursor = 0;
  const open: typeof intervals = [];

  for (let index = 0; index + 1 < edges.length; index += 1) {
    const left = edges[index];
    const right = edges[index + 1];
    while (cursor < byStart.length && byStart[cursor].start <= left) open.push(byStart[cursor++]);
    let best = Infinity;
    for (let each = open.length - 1; each >= 0; each -= 1) {
      if (open[each].end <= left) open.splice(each, 1);
      else best = Math.min(best, open[each].rank);
    }
    if (best !== Infinity) totals[best] += right - left;
  }

  return {
    parts: timeParts.map((part, index) => ({ ...part, ms: totals[index] })),
    kinds: [...kinds.values()].filter((kind) => kind.ms > 0).toSorted((a, b) => b.ms - a.ms),
  };
}

// ---- context on each model call ----

export interface ContextPoint {
  step: ModelStep;
  index: number;
  context: number;
  share: number;
  rebuilt: boolean;
  compacted: boolean;
}

export function contextSeries(session: Session): ContextPoint[] {
  const points: ContextPoint[] = [];
  let compactedBefore = false;

  for (const step of session.steps) {
    if (step.kind !== 'model') continue;
    if (step.thread === 'side' && step.purpose === 'compact') {
      compactedBefore = true;
      continue;
    }
    if (step.thread !== 'main') continue;

    const context = step.inputTokens + step.cacheReadTokens + step.cacheCreationTokens;
    points.push({
      step,
      index: points.length,
      context,
      share: context / session.contextLimit,
      // Most of the context written again: the cache expired, or the context was replaced.
      rebuilt: points.length > 0 && step.cacheCreationTokens > 20000 && step.cacheCreationTokens > 0.5 * context,
      compacted: compactedBefore,
    });
    compactedBefore = false;
  }

  return points;
}

// ---- skill activations ----

export interface Activation {
  index: number;
  step: SkillStep;
  prompt: PromptSpan;
  startMs: number;
  endMs: number;
  // The skill in force when this one fired, so a nested skill can name the one that called it.
  calledFrom: string | null;
  steps: SessionStep[];
  modelCalls: number;
  toolCalls: number;
  failedTools: number;
  subagents: number;
  costUsd: number;
  files: { file: string; edits: number }[];
}

// An activation runs until the next skill fires in the same prompt, or the prompt ends.
export function activations(session: Session): Activation[] {
  const skills = session.steps.filter((step): step is SkillStep => step.kind === 'skill');

  return skills.map((step, index) => {
    const prompt = session.prompts[step.prompt];
    const next = skills[index + 1];
    const endMs = next !== undefined && next.prompt === step.prompt ? next.at : prompt.endMs;
    const previous = skills[index - 1];
    const steps = session.steps.filter((each) => each.at > step.at && startOf(each) < endMs && each.prompt === step.prompt);
    const files = new Map<string, number>();

    for (const each of steps) {
      if (each.kind === 'tool' && each.family === 'edit') files.set(each.summary, (files.get(each.summary) ?? 0) + 1);
    }

    return {
      index,
      step,
      prompt,
      startMs: step.at,
      endMs,
      calledFrom: step.trigger === 'nested-skill' && previous?.prompt === step.prompt ? previous.skill : null,
      steps,
      modelCalls: steps.filter((each) => each.kind === 'model' && each.thread !== 'side').length,
      toolCalls: steps.filter((each) => each.kind === 'tool').length,
      failedTools: steps.filter((each) => each.kind === 'tool' && !each.ok).length,
      subagents: steps.filter((each) => each.kind === 'subagent').length,
      costUsd: steps.reduce((sum, each) => sum + (each.kind === 'model' && each.thread !== 'side' ? each.costUsd : 0), 0),
      files: [...files.entries()].map(([file, edits]) => ({ file, edits })).toSorted((a, b) => b.edits - a.edits),
    };
  });
}

// ---- the conversation ----

export interface Exchange {
  prompt: PromptStep;
  span: PromptSpan;
  skills: SkillStep[];
  turns: { call: ModelStep; tools: ToolStep[] }[];
  answer: ModelStep | null;
  subagents: SubagentStep[];
}

export function conversation(session: Session): Exchange[] {
  const tools = new Map<string, ToolStep>();
  for (const step of session.steps) {
    if (step.kind === 'tool') tools.set(step.toolUseId, step);
  }

  return session.prompts.map((span) => {
    const inPrompt = session.steps.filter((step) => step.prompt === span.index);
    const calls = inPrompt.filter((step): step is ModelStep => step.kind === 'model' && step.thread === 'main');
    const turns = calls.map((call) => ({ call, tools: call.toolUseIds.flatMap((id) => tools.get(id) ?? []) }));

    return {
      prompt: inPrompt.find((step): step is PromptStep => step.kind === 'prompt')!,
      span,
      skills: inPrompt.filter((step): step is SkillStep => step.kind === 'skill'),
      turns,
      answer: calls.toReversed().find((call) => call.stopReason === 'end_turn') ?? null,
      subagents: inPrompt.filter((step): step is SubagentStep => step.kind === 'subagent'),
    };
  });
}

// ---- the trace ----

export type SpanName = 'interaction' | 'llm_request' | 'tool' | 'tool.blocked_on_user' | 'tool.execution' | 'hook' | 'subagent' | 'error';

export interface TraceRow {
  id: string;
  name: SpanName;
  label: string;
  depth: number;
  startMs: number;
  endMs: number;
  step: SessionStep | null;
  failed: boolean;
}

export interface Trace {
  prompt: PromptSpan;
  startMs: number;
  endMs: number;
  rows: TraceRow[];
}

const spanName = (step: SessionStep): SpanName =>
  step.kind === 'model' ? 'llm_request' : step.kind === 'tool' || step.kind === 'rejected' ? 'tool' : step.kind === 'hook' ? 'hook' : step.kind === 'subagent' ? 'subagent' : step.kind === 'modelError' ? 'error' : 'interaction';

export function spanLabel(step: SessionStep): string {
  switch (step.kind) {
    case 'prompt':
      return step.command ? `/${step.command}` : step.said.text ?? `Prompt ${step.prompt + 1}`;
    case 'model':
      return `${step.thread === 'main' ? 'main' : step.purpose} · ${format.model(step.model)} · ${step.stopReason}`;
    case 'tool':
      return `${step.tool} · ${step.summary}`;
    case 'rejected':
      return `${step.tool} · rejected · ${step.summary}`;
    case 'hook':
      return step.hook;
    case 'subagent':
      return `${step.agentType} · ${step.description}`;
    case 'modelError':
      return `API ${step.status}`;
    case 'skill':
      return `Skill · ${step.skill}`;
  }
}

// One prompt is one trace. Skill events are not spans, so they stay out of the tree.
export function traceFor(session: Session, stepId: string): Trace | null {
  const target = session.steps.find((step) => step.id === stepId);
  if (target === undefined || target.prompt < 0) return null;

  const prompt = session.prompts[target.prompt];
  const inPrompt = session.steps.filter((step) => step.prompt === target.prompt && step.kind !== 'skill');
  const root = inPrompt.find((step) => step.kind === 'prompt');
  if (root === undefined) return null;

  const known = new Set(inPrompt.map((step) => step.id));
  const children = new Map<string, SessionStep[]>();
  for (const step of inPrompt) {
    if (step === root) continue;
    // A subagent still running has written no event yet, so its work hangs off the prompt until it does.
    const parent = step.parent !== null && known.has(step.parent) ? step.parent : root.id;
    children.set(parent, [...(children.get(parent) ?? []), step]);
  }

  const rows: TraceRow[] = [];
  const walk = (step: SessionStep, depth: number) => {
    const isRoot = step === root;
    rows.push({
      id: step.id,
      name: isRoot ? 'interaction' : spanName(step),
      label: spanLabel(step),
      depth,
      startMs: isRoot ? prompt.startMs : startOf(step),
      endMs: isRoot ? prompt.endMs : step.at,
      step,
      failed: (step.kind === 'tool' && !step.ok) || step.kind === 'modelError' || step.kind === 'rejected' || (step.kind === 'hook' && step.blocking > 0),
    });

    if (step.kind === 'tool') {
      const pre = (children.get(step.id) ?? []).filter((each) => each.kind === 'hook' && each.hook.startsWith('Pre'));
      for (const hook of pre) walk(hook, depth + 1);
      if (step.waitedMs > 0) {
        rows.push({ id: `${step.id}:wait`, name: 'tool.blocked_on_user', label: 'waiting for your OK', depth: depth + 1, startMs: startOf(step), endMs: startOf(step) + step.waitedMs, step: null, failed: false });
      }
      rows.push({ id: `${step.id}:run`, name: 'tool.execution', label: step.ok ? 'ran' : step.error ?? 'failed', depth: depth + 1, startMs: startOf(step) + step.waitedMs, endMs: step.at, step: null, failed: !step.ok });
      for (const each of (children.get(step.id) ?? []).filter((child) => !pre.includes(child)).toSorted((a, b) => startOf(a) - startOf(b))) walk(each, depth + 1);
      return;
    }

    for (const each of (children.get(step.id) ?? []).toSorted((a, b) => startOf(a) - startOf(b))) walk(each, depth + 1);
  };
  walk(root, 0);

  return { prompt, startMs: prompt.startMs, endMs: prompt.endMs, rows };
}

// ---- findings ----

export interface Finding {
  key: string;
  tone: 'failed' | 'warned' | 'info';
  title: string;
  detail: string;
  stepIds: string[];
}

export function findings(session: Session): Finding[] {
  const found: Finding[] = [];
  const tools = session.steps.filter((step): step is ToolStep => step.kind === 'tool');

  const failing = new Map<string, ToolStep[]>();
  for (const tool of tools.filter((each) => !each.ok && each.family === 'shell')) failing.set(tool.summary, [...(failing.get(tool.summary) ?? []), tool]);
  for (const [command, runs] of failing) {
    if (runs.length >= 3) found.push({ key: `fail:${command}`, tone: 'failed', title: `Ran the same failing command ${runs.length} times`, detail: command, stepIds: runs.map((run) => run.id) });
  }

  const edits = new Map<string, ToolStep[]>();
  for (const tool of tools.filter((each) => each.family === 'edit')) edits.set(tool.summary, [...(edits.get(tool.summary) ?? []), tool]);
  for (const [file, runs] of edits) {
    if (runs.length >= 6) found.push({ key: `edit:${file}`, tone: 'warned', title: `Edited one file ${runs.length} times`, detail: file, stepIds: runs.map((run) => run.id) });
  }

  const blocked = tools.filter((tool) => tool.errorType === 'HookBlocked');
  if (blocked.length > 0) found.push({ key: 'blocked', tone: 'warned', title: `A policy hook blocked ${blocked.length} tool call${blocked.length > 1 ? 's' : ''}`, detail: blocked[0].summary, stepIds: blocked.map((tool) => tool.id) });

  const limits = session.steps.filter((step) => step.kind === 'modelError');
  if (limits.length > 0) found.push({ key: 'limits', tone: 'failed', title: `Hit the rate limit ${limits.length} time${limits.length > 1 ? 's' : ''}`, detail: 'API 429, retried after a pause', stepIds: limits.map((step) => step.id) });

  const split = timeSplit(session);
  const busy = split.parts.filter((part) => part.key !== 'yourTurn' && part.key !== 'quiet').reduce((sum, part) => sum + part.ms, 0);
  const hookMs = split.kinds.find((kind) => kind.key === 'hook')?.ms ?? 0;
  if (busy > 0 && hookMs / busy >= 0.08) {
    found.push({ key: 'hooks', tone: 'warned', title: `Hooks took ${format.percent(hookMs / busy)} of the busy time`, detail: `${format.duration(hookMs)} across ${session.steps.filter((step) => step.kind === 'hook').length} runs`, stepIds: [] });
  }

  const waiting = split.parts.find((part) => part.key === 'waiting')?.ms ?? 0;
  const rejected = session.steps.filter((step) => step.kind === 'rejected');
  if (waiting >= minute || rejected.length > 0) {
    found.push({ key: 'waiting', tone: 'info', title: `Waited ${format.duration(waiting)} for permission`, detail: rejected.length > 0 ? `${rejected.length} call${rejected.length > 1 ? 's' : ''} rejected` : 'Every call was allowed in the end', stepIds: rejected.map((step) => step.id) });
  }

  const context = contextSeries(session);
  const rebuilt = context.filter((point) => point.rebuilt);
  if (rebuilt.length >= 2) {
    found.push({ key: 'cache', tone: 'info', title: `Rebuilt the prompt cache ${rebuilt.length} times`, detail: `${format.usd(rebuilt.reduce((sum, point) => sum + point.step.costUsd, 0))} on those calls`, stepIds: rebuilt.map((point) => point.step.id) });
  }

  const peak = Math.max(0, ...context.map((point) => point.share));
  if (peak >= 0.4 || context.some((point) => point.compacted)) {
    found.push({ key: 'context', tone: 'info', title: `Context peaked at ${format.percent(peak)} of the limit`, detail: context.some((point) => point.compacted) ? 'Compacted once' : 'No compaction', stepIds: [] });
  }

  return found;
}

// ---- hover details ----

export interface Description {
  title: string;
  when: string;
  rows: [string, string][];
  said: { label: string; said: Said } | null;
  code: string | null;
  tone: 'failed' | 'warned' | null;
}

export function describe(step: SessionStep, session: Session): Description {
  const when = `${format.clock(startOf(step), true)}${step.ms > 0 ? ` · ${format.duration(step.ms)}` : ''}`;
  const base = { when, said: null, code: null, tone: null };

  switch (step.kind) {
    case 'prompt':
      return { ...base, title: `Prompt ${step.prompt + 1}${step.command ? ` · /${step.command}` : ''}`, rows: [['Length', `${format.int(step.said.length)} characters`]], said: { label: 'What was typed', said: step.said } };
    case 'model': {
      const context = step.inputTokens + step.cacheReadTokens + step.cacheCreationTokens;
      return {
        ...base,
        title: `Model call · ${format.model(step.model)}`,
        rows: [
          ['Asked by', step.thread === 'main' ? 'main thread' : step.thread === 'subagent' ? `${step.purpose} subagent` : step.purpose.replaceAll('_', ' ')],
          ['Context', `${format.tokens(context)} · ${format.percent(context / session.contextLimit)} of limit`],
          ['From cache', format.tokens(step.cacheReadTokens)],
          ['Written to cache', format.tokens(step.cacheCreationTokens)],
          ['Output', `${format.int(step.outputTokens)} tokens`],
          ['First token', format.duration(step.ttftMs)],
          ['Stopped', step.stopReason],
          ['Cost', format.usd(step.costUsd)],
          ['Skill in force', step.skill ?? 'none'],
        ],
        said: step.said === null ? null : { label: 'What the model wrote', said: step.said },
      };
    }
    case 'modelError':
      return { ...base, title: `API ${step.status}`, rows: [['Model', format.model(step.model)]], code: step.message, tone: 'failed' };
    case 'tool':
      return {
        ...base,
        title: `${step.tool} · ${step.ok ? 'worked' : 'failed'}`,
        rows: [
          ['Ran for', format.duration(step.ms - step.waitedMs)],
          ...(step.waitedMs > 0 ? ([['Waited for OK', format.duration(step.waitedMs)]] as [string, string][]) : []),
          ['Sent', format.bytes(step.inputBytes)],
          ['Got back', format.bytes(step.outputBytes)],
          ['By', step.agent === null ? 'main thread' : 'a subagent'],
        ],
        code: step.summary,
        tone: step.ok ? null : 'failed',
      };
    case 'rejected':
      return { ...base, title: `${step.tool} · rejected`, rows: [['Decided by', step.source]], code: step.summary, tone: 'warned' };
    case 'hook':
      return { ...base, title: `Hook · ${step.hook}`, rows: [['Hooks run', String(step.hooks)], ['Blocked', String(step.blocking)]], tone: step.blocking > 0 ? 'warned' : null };
    case 'skill':
      return { ...base, title: `Skill fired · ${step.skill}`, rows: [['Why', format.trigger(step.trigger)], ['Loaded from', step.source]] };
    case 'subagent':
      return {
        ...base,
        title: `Subagent · ${step.agentType}`,
        rows: [
          ['Task', step.description],
          ['Tool calls', String(step.toolUses)],
          ['Tokens', format.tokens(step.tokens)],
          ['Model', format.model(step.model)],
          ['In background', step.async ? 'yes' : 'no'],
        ],
      };
  }
}

// ---- a time axis that folds idle stretches ----

export interface FoldScale {
  map: (ms: number) => number;
  invert: (px: number) => number;
  segments: [number, number][];
  pixels: [number, number][];
  gaps: { x: number; fromMs: number; toMs: number }[];
  msPerPx: number;
}

// Without the fold, an eleven-hour session is one thin smear of work between long empty stretches.
export function foldScale(intervals: [number, number][], x0: number, x1: number, foldMs = 3 * minute): FoldScale {
  const sorted = intervals.filter(([a, b]) => Number.isFinite(a) && Number.isFinite(b)).toSorted((a, b) => a[0] - b[0]);
  const segments: [number, number][] = [];

  for (const [start, end] of sorted) {
    const last = segments[segments.length - 1];
    if (last && start - last[1] <= foldMs) last[1] = Math.max(last[1], end);
    else segments.push([start, Math.max(start, end)]);
  }
  if (segments.length === 0) segments.push([0, 1000]);

  const pad = Math.max(500, (segments[segments.length - 1][1] - segments[0][0]) * 0.004);
  for (const segment of segments) {
    segment[0] -= pad;
    segment[1] += pad;
  }

  const gapCount = segments.length - 1;
  const gapPx = gapCount > 0 ? Math.min(22, ((x1 - x0) * 0.2) / gapCount) : 0;
  const total = segments.reduce((sum, [a, b]) => sum + (b - a), 0);
  const available = x1 - x0 - gapPx * gapCount;
  const pixels: [number, number][] = [];
  let x = x0;

  for (const [a, b] of segments) {
    const width = ((b - a) / total) * available;
    pixels.push([x, x + width]);
    x += width + gapPx;
  }

  const find = (ms: number) => {
    let low = 0;
    let high = segments.length - 1;
    let found = -1;
    while (low <= high) {
      const middle = (low + high) >> 1;
      if (segments[middle][0] <= ms) {
        found = middle;
        low = middle + 1;
      } else high = middle - 1;
    }
    return found;
  };

  const map = (ms: number) => {
    const index = find(ms);
    if (index < 0) return x0;
    const [a, b] = segments[index];
    if (ms <= b) return pixels[index][0] + ((ms - a) / (b - a)) * (pixels[index][1] - pixels[index][0]);
    if (index + 1 < segments.length) return pixels[index][1] + ((ms - b) / (segments[index + 1][0] - b)) * gapPx;
    return pixels[index][1];
  };

  const invert = (px: number) => {
    for (let index = 0; index < pixels.length; index += 1) {
      const [left, right] = pixels[index];
      if (px <= right || index === pixels.length - 1) {
        const clamped = Math.max(left, Math.min(right, px));
        return segments[index][0] + ((clamped - left) / Math.max(1, right - left)) * (segments[index][1] - segments[index][0]);
      }
    }
    return segments[0][0];
  };

  return {
    map,
    invert,
    segments,
    pixels,
    gaps: segments.slice(1).map((segment, index) => ({ x: pixels[index][1] + gapPx / 2, fromMs: segments[index][1], toMs: segment[0] })),
    msPerPx: total / Math.max(1, available),
  };
}

export function ticks(scale: FoldScale, minGapPx = 64): { x: number; ms: number; label: string }[] {
  const steps = [5 * second, 10 * second, 30 * second, minute, 2 * minute, 5 * minute, 10 * minute, 15 * minute, 30 * minute, hour, 2 * hour];
  const step = steps.find((each) => each / scale.msPerPx >= 90) ?? 2 * hour;
  const out: { x: number; ms: number; label: string }[] = [];
  let lastX = -Infinity;

  for (const [a, b] of scale.segments) {
    for (let ms = Math.ceil(a / step) * step; ms <= b; ms += step) {
      const x = scale.map(ms);
      if (x - lastX < minGapPx) continue;
      out.push({ x, ms, label: format.clock(ms, step < minute) });
      lastX = x;
    }
  }

  return out;
}

export const sessionIntervals = (steps: SessionStep[]): [number, number][] => steps.map((step) => [startOf(step), step.at]);
