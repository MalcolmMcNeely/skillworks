import { describe, expect, it } from 'vitest';
import { describeCount, describeMoney, describeTokens } from './skills';

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
