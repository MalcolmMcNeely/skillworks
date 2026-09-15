import type { Span } from '../../filters/lib/filters';
import type { AnswerEnd } from '../../gaps/lib/gaps';
import type { Origin } from '../../provenance/lib/provenance';

export interface TokenSplit {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheCreationTokens: number;
}

export interface TurnTotals extends TokenSplit {
  // US dollars, as Claude Code estimated them.
  cost: number;
}

export interface SkillOnDay {
  name: string;
  activations: number;
  // By UTC hour, as the Filter counts whole UTC days.
  hours: number[];
  repositories: string[];
  // Null where the skill's Turns went unnamed, as an empty list or a zero would say it spent nothing.
  models: string[] | null;
  efforts: string[] | null;
  spend: TurnTotals | null;
  origins: Origin[];
}

export interface SkillSummary extends Omit<SkillOnDay, 'hours'> {
  each: number | null;
  // Only to the hour, as a day line counts no finer.
  lastFired: string | null;
}

export interface SkillsHead {
  kind: 'head';
  span: Span & { lookback: boolean; fromUtc: string; untilUtc: string };
  // Newest first, the order the days arrive in.
  days: string[];
  catalogueSkills: string[];
}

export interface SkillsDay {
  kind: 'day';
  day: string;
  skills: SkillOnDay[];
  // Null when the filter names a skill, as some of it may not be that skill's.
  unnamedSpend: TurnTotals | null;
  unnarrowedEvents: number;
}

export type SkillsLine = SkillsHead | SkillsDay | AnswerEnd;

// Words, not a zero or a dash: a plugin outside Anthropic's marketplaces has its Turns sent unnamed, so what it spent is not known.
export const notNamed = 'Not named';

// Not the reader's locale: costs are in US dollars, so figures group and point the way dollars do.
const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  // Four places, or a firing that costs a fraction of a cent would round to free.
  maximumFractionDigits: 4,
});

const counts = new Intl.NumberFormat('en-US');

const tokenCounts = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

export function describeMoney(amount: number | null): string {
  return amount === null ? notNamed : money.format(amount);
}

export function describeCount(count: number): string {
  return counts.format(count);
}

export function describeTokens(count: number): string {
  return tokenCounts.format(count);
}
