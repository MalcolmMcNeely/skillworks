import { describe, expect, it } from 'vitest';
import type { SkillSummary, TurnTotals } from './skills';
import { totalsOf } from './totals';

function spent(cost: number, tokens: number): TurnTotals {
  return { cost, inputTokens: tokens, outputTokens: tokens, cacheReadTokens: tokens, cacheCreationTokens: tokens };
}

function skill(name: string, activations: number, spend: TurnTotals | null): SkillSummary {
  return { name, activations, repositories: [], models: [], efforts: [], spend, averageCost: null, origins: [] };
}

const skills = [skill('alpha', 3, spent(1.5, 10)), skill('beta', 1, spent(0.5, 5)), skill('gamma', 4, null)];

describe('totalsOf', () => {
  it('counts Cost, Activations, Skills and every kind of token, Unnamed spend included', () => {
    const totals = totalsOf({ skills, unnamedSpend: spent(2, 25) });

    expect(totals).toMatchObject({ cost: 4, activations: 8, skills: 3, tokens: 160 });
  });

  it('works out Each from the Cost and Activations beside it, so the rail agrees with itself', () => {
    expect(totalsOf({ skills, unnamedSpend: spent(2, 25) }).each).toBe(0.5);
  });

  it('shows Unnamed spend only when there is some', () => {
    expect(totalsOf({ skills, unnamedSpend: spent(2, 25) }).unnamedSpend).toBe(2);
    expect(totalsOf({ skills, unnamedSpend: spent(0, 0) }).unnamedSpend).toBeNull();
    expect(totalsOf({ skills, unnamedSpend: null }).unnamedSpend).toBeNull();
  });

  it('has no Each when nothing fired, rather than dividing by zero', () => {
    expect(totalsOf({ skills: [skill('alpha', 0, spent(1, 1))], unnamedSpend: null }).each).toBeNull();
  });
});
