import { describe, expect, it } from 'vitest';
import { readoutRows } from './readout';
import { describeCount, describeEach, describeMoney, describeTokens, type SkillSummary, type TurnTotals } from './skills';
import { totalsOf } from './totals';

const spent: TurnTotals = { cost: 1, inputTokens: 100, outputTokens: 200, cacheReadTokens: 300, cacheCreationTokens: 400 };

const now = Date.parse('2026-09-15T12:00:00Z');

function skill(more: Partial<SkillSummary> = {}): SkillSummary {
  return {
    name: 'grilling',
    activations: 4,
    triggers: [],
    repositories: [],
    models: [],
    efforts: [],
    spend: spent,
    origins: [],
    each: 0.25,
    lastFired: '2026-09-15T09:00:00Z',
    spark: [],
    ...more,
  };
}

function railEach(only: SkillSummary): string {
  return describeEach(totalsOf({ skills: [only], unnamedSpend: null }));
}

function readoutEach(only: SkillSummary): string | undefined {
  return readoutRows(only, now).find((row) => row.label === 'Each')?.value;
}

describe('describeMoney', () => {
  it('shows the pennies', () => {
    expect(describeMoney(14.5215)).toBe('$14.5215');
    expect(describeMoney(0)).toBe('$0.00');
  });

  it('keeps a fraction of a penny rather than rounding it away to free', () => {
    expect(describeMoney(0.0022)).toBe('$0.0022');
  });

  it('says not named, never $0.00, when Claude Code did not name the skill on its Turns', () => {
    expect(describeMoney(null)).toBe('Not named');
  });
});

describe('describeEach', () => {
  it('says None for a figure that never fired, so the reader looks at its description', () => {
    expect(describeEach({ each: null, activations: 0 })).toBe('None');
  });

  it('says Not named for a figure that fired on spend Claude Code will not name', () => {
    expect(describeEach({ each: null, activations: 3 })).toBe('Not named');
  });

  it('shows the figure when there is one', () => {
    expect(describeEach({ each: 0.25, activations: 4 })).toBe('$0.25');
  });

  it('keeps the dash for no answer at all, so an outage never reads as a quiet week', () => {
    expect(describeEach(null)).toBe('—');
  });
});

describe('the Each the rail and the readout read', () => {
  it('agrees for a skill that spent but never fired', () => {
    const never = skill({ activations: 0, each: null, lastFired: null });

    expect([railEach(never), readoutEach(never)]).toEqual(['None', 'None']);
  });

  it('agrees for a skill whose Turns went unnamed', () => {
    const hidden = skill({ spend: null, models: null, efforts: null, each: null });

    expect([railEach(hidden), readoutEach(hidden)]).toEqual(['Not named', 'Not named']);
  });

  it('agrees for a skill that fired', () => {
    const fired = skill();

    expect([railEach(fired), readoutEach(fired)]).toEqual(['$0.25', '$0.25']);
  });
});

describe('describeCount', () => {
  it('groups the thousands, so a figure on a tile reads at a glance', () => {
    expect(describeCount(1234567)).toBe('1,234,567');
  });
});

describe('describeTokens', () => {
  it('shortens a large count to fit a rail instrument', () => {
    expect(describeTokens(3_412_000)).toBe('3.4M');
    expect(describeTokens(12_500)).toBe('12.5K');
  });

  it('leaves a small count whole', () => {
    expect(describeTokens(950)).toBe('950');
  });
});
