import type { SkillSummary, TurnTotals } from './skills';

export interface Totals {
  cost: number;
  activations: number;
  skills: number;
  tokens: number;
  each: number | null;
  unnamedSpend: number | null;
}

export function tokensIn(spend: TurnTotals | null): number {
  return spend === null
    ? 0
    : spend.inputTokens + spend.outputTokens + spend.cacheReadTokens + spend.cacheCreationTokens;
}

// Unnamed spend is in the Cost, because its Activations are in the count beside it.
export function totalsOf(answer: { skills: readonly SkillSummary[]; unnamedSpend: TurnTotals | null }): Totals {
  const unnamed = answer.unnamedSpend?.cost ?? 0;
  const cost = answer.skills.reduce((sum, skill) => sum + (skill.spend?.cost ?? 0), unnamed);
  const activations = answer.skills.reduce((sum, skill) => sum + skill.activations, 0);

  return {
    cost,
    activations,
    skills: answer.skills.length,
    tokens: answer.skills.reduce((sum, skill) => sum + tokensIn(skill.spend), tokensIn(answer.unnamedSpend)),
    each: activations === 0 ? null : cost / activations,
    unnamedSpend: unnamed > 0 ? unnamed : null,
  };
}
