import type { SymbolTable } from '../../shared/alphabets/lib/alphabets';
import { describeMoney } from '../../shared/figures/lib/figures';
import type { Span } from '../../shared/filters/lib/filters';
import { missingWords, type GapEnd } from '../../shared/gaps/lib/gaps';
import type { Origin, TriggerCount } from '../../shared/provenance/lib/provenance';

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
  pluginSkills: string[];
}

export interface SkillsDay {
  kind: 'day';
  day: string;
  skills: SkillOnDay[];
  // Null when the filter names a skill, as some of it may not be that skill's.
  unnamedSpend: TurnTotals | null;
  unnarrowedEvents: number;
}

export type SkillsLine = SkillsHead | SkillsDay | GapEnd;

// The dash is drawn, so it answers to the alphabets as any other mark on screen does.
export const missingSymbols: SymbolTable = { alphabet: 'condition', glyphs: [missingWords.noAnswer] };

// A Turn sent unnamed has a Cost nobody can attribute, which is hidden rather than absent.
export function describeSpend(amount: number | null): string {
  return amount === null ? missingWords.notNamed : describeMoney(amount);
}

// A Cost with nothing to share it across is not a Cost that went unnamed.
export function describeEach(figures: { each: number | null; activations: number } | null): string {
  if (figures === null) {
    return missingWords.noAnswer;
  }

  return figures.activations === 0 ? missingWords.none : describeSpend(figures.each);
}
