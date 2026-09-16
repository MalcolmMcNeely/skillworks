import type { SymbolTable } from '../../alphabets/lib/alphabets';
import type { Span } from '../../filters/lib/filters';
import type { AnswerEnd } from '../../gaps/lib/gaps';
import type { Origin, TriggerCount } from '../../provenance/lib/provenance';

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
  triggers: TriggerCount[];
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
  // One count per slice of the activity strip, for the chart on the skill's tile.
  spark: number[];
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

export const missingWords = {
  // A word, not a dash, which a screen reader reads as a pause or not at all.
  none: 'None',
  // A plugin outside Anthropic's marketplaces has its Turns sent unnamed, so the cost is hidden, not absent.
  notNamed: 'Not named',
  // Never a zero, so an outage never reads as a quiet week.
  noAnswer: '—',
} as const;

// The dash is drawn, so it answers to the alphabets as any other mark on screen does.
export const missingSymbols: SymbolTable = { alphabet: 'condition', glyphs: [missingWords.noAnswer] };

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
  return amount === null ? missingWords.notNamed : money.format(amount);
}

// A Cost with nothing to share it across is not a Cost that went unnamed.
export function describeEach(figures: { each: number | null; activations: number } | null): string {
  if (figures === null) {
    return missingWords.noAnswer;
  }

  return figures.activations === 0 ? missingWords.none : describeMoney(figures.each);
}

export function describeCount(count: number): string {
  return counts.format(count);
}

export function describeTokens(count: number): string {
  return tokenCounts.format(count);
}
