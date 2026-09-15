// PROTOTYPE — throwaway. Answers "what should the at-a-glance telemetry screen look like?".
// Pure helpers every variant may use. Nothing here is tested, and none of it ships as is.

import type { Activation } from '../../activations/api/activations';
import type { Filter, Span } from '../../filters/lib/filters';
import type { GapKind } from '../../gaps/lib/gaps';
import type { Part, PartState } from '../../health/lib/health';
import type { SkillSummary } from '../api/skills';
import type { TurnTotals } from '../lib/skills';

const dayMs = 24 * 60 * 60 * 1000;

export type TriggerKey = 'claude-proactive' | 'user-slash' | 'nested-skill' | 'agent-preload' | 'unknown';

export const triggerKeys: TriggerKey[] = ['claude-proactive', 'user-slash', 'nested-skill', 'agent-preload', 'unknown'];

export const triggerMarks: Record<TriggerKey, { glyph: string; label: string }> = {
  'claude-proactive': { glyph: '✦', label: 'Claude chose it' },
  'user-slash': { glyph: '/', label: 'Typed' },
  'nested-skill': { glyph: '↳', label: 'Called by a skill' },
  'agent-preload': { glyph: '◈', label: 'Given to an agent' },
  unknown: { glyph: '?', label: 'Not recorded' },
};

export function triggerOf(activation: Activation): TriggerKey {
  const trigger = activation.origin.trigger;

  return trigger !== null && trigger in triggerMarks ? (trigger as TriggerKey) : 'unknown';
}

export type TriggerCounts = Record<TriggerKey, number>;

export function countTriggers(activations: readonly Activation[]): TriggerCounts {
  const counts: TriggerCounts = { 'claude-proactive': 0, 'user-slash': 0, 'nested-skill': 0, 'agent-preload': 0, unknown: 0 };

  for (const activation of activations) {
    counts[triggerOf(activation)] += 1;
  }

  return counts;
}

export function firingsOf(activations: readonly Activation[], skill: string): Activation[] {
  return activations.filter((activation) => activation.skill === skill);
}

export interface Totals {
  firings: number;
  cost: number;
  tokens: number;
  skills: number;
  priciest: number;
  busiest: number;
}

export function tokensIn(spend: TurnTotals | null): number {
  return spend === null
    ? 0
    : spend.inputTokens + spend.outputTokens + spend.cacheReadTokens + spend.cacheCreationTokens;
}

export function totalsOf(skills: readonly SkillSummary[]): Totals {
  return {
    firings: skills.reduce((sum, skill) => sum + skill.activations, 0),
    cost: skills.reduce((sum, skill) => sum + (skill.spend?.cost ?? 0), 0),
    tokens: skills.reduce((sum, skill) => sum + tokensIn(skill.spend), 0),
    skills: skills.length,
    priciest: Math.max(0, ...skills.map((skill) => skill.spend?.cost ?? 0)),
    busiest: Math.max(0, ...skills.map((skill) => skill.activations)),
  };
}

export interface Timeframe {
  start: number;
  end: number;
  days: number;
}

export function timeframeOf(span: Span): Timeframe {
  const start = Date.parse(`${span.from}T00:00:00Z`);
  const end = Date.parse(`${span.to}T00:00:00Z`) + dayMs;

  return { start, end, days: Math.round((end - start) / dayMs) };
}

// 0 at the start of the span, 1 at its end.
export function positionIn(frame: Timeframe, timestampUtc: string): number {
  return Math.min(1, Math.max(0, (Date.parse(timestampUtc) - frame.start) / (frame.end - frame.start)));
}

export function binCounts(activations: readonly Activation[], frame: Timeframe, bins: number): number[] {
  const counts = Array.from({ length: bins }, () => 0);

  for (const activation of activations) {
    const index = Math.min(bins - 1, Math.floor(positionIn(frame, activation.timestampUtc) * bins));
    counts[index] += 1;
  }

  return counts;
}

export function dayLabels(frame: Timeframe): string[] {
  return Array.from({ length: frame.days }, (_, day) =>
    new Date(frame.start + day * dayMs).toLocaleDateString('en-GB', { weekday: 'short', timeZone: 'UTC' }),
  );
}

export function lastFired(activations: readonly Activation[], skill: string): string | null {
  let latest: string | null = null;

  for (const activation of activations) {
    if (activation.skill === skill && (latest === null || activation.timestampUtc > latest)) {
      latest = activation.timestampUtc;
    }
  }

  return latest;
}

export function ago(timestampUtc: string, now = Date.now()): string {
  const minutes = Math.max(0, Math.round((now - Date.parse(timestampUtc)) / 60000));

  if (minutes < 60) {
    return `${minutes}m`;
  }

  const hours = Math.round(minutes / 60);

  return hours < 48 ? `${hours}h` : `${Math.round(hours / 24)}d`;
}

export function money(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) {
    return '—';
  }

  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(1)}k`;
  }

  return `$${amount.toFixed(amount >= 100 ? 0 : 2)}`;
}

export function compact(count: number): string {
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(count);
}

export type SpanChoice = '1d' | '7d' | '30d' | 'custom';

export const spanChoices: { key: Exclude<SpanChoice, 'custom'>; label: string }[] = [
  { key: '1d', label: '24H' },
  { key: '7d', label: '7D' },
  { key: '30d', label: '30D' },
];

function utcDay(offsetDays: number): string {
  return new Date(Date.now() - offsetDays * dayMs).toISOString().slice(0, 10);
}

export function spanChoiceOf(filter: Filter): SpanChoice {
  if (filter.from === '' && filter.to === '') {
    return '7d';
  }

  if (filter.to === utcDay(0) && filter.from === utcDay(0)) {
    return '1d';
  }

  return filter.to === utcDay(0) && filter.from === utcDay(29) ? '30d' : 'custom';
}

export function withSpan(filter: Filter, choice: Exclude<SpanChoice, 'custom'>): Filter {
  if (choice === '7d') {
    return { ...filter, from: '', to: '' };
  }

  return { ...filter, from: utcDay(choice === '1d' ? 0 : 29), to: utcDay(0) };
}

// One word per state, as a game HUD says it. The Gap's own sentence stays available for a tooltip.
export type Signal = 'live' | 'offline' | 'dark' | 'unsure' | 'quiet' | 'clipped';

export const signalWords: Record<Signal, string> = {
  live: 'Live',
  offline: 'No signal',
  dark: 'Telemetry off',
  unsure: 'Telemetry unknown',
  quiet: 'Quiet',
  clipped: 'Partial',
};

export function signalOf(kind: GapKind): Signal {
  const signals: Record<GapKind, Signal> = {
    complete: 'live',
    unreachable: 'offline',
    telemetryOff: 'dark',
    telemetryUnknown: 'unsure',
    quiet: 'quiet',
    truncated: 'clipped',
  };

  return signals[kind];
}

export const partMarks: Record<PartState, { glyph: string; label: string }> = {
  working: { glyph: '●', label: 'Working' },
  starting: { glyph: '◌', label: 'Starting' },
  off: { glyph: '○', label: 'Off' },
  broken: { glyph: '✕', label: 'Broken' },
};

// Short call signs for the parts Studio reports today; an unknown part keeps its own name.
export function callSign(part: Part): string {
  const signs: Record<string, string> = {
    'Events store': 'Store',
    'Claude Code telemetry': 'Telemetry',
    Catalogue: 'Catalogue',
  };

  return signs[part.name] ?? part.name;
}
