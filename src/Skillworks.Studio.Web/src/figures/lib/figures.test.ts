import { describe, expect, it } from 'vitest';
import { describeCount, describeMoney, describeShare, describeStretch, describeTokens } from './figures';

describe('describeMoney', () => {
  it('shows the pennies', () => {
    expect(describeMoney(14.5215)).toBe('$14.5215');
    expect(describeMoney(0)).toBe('$0.00');
  });

  it('keeps a fraction of a penny rather than rounding it away to free', () => {
    expect(describeMoney(0.0022)).toBe('$0.0022');
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

describe('describeShare', () => {
  it('reads a share as whole percent', () => {
    expect(describeShare(0.4236)).toBe('42%');
  });
});

describe('describeStretch', () => {
  it('counts a stretch under a second in milliseconds', () => {
    expect(describeStretch(4)).toBe('4 ms');
  });

  it('counts a short stretch in seconds, to a place while that place still says something', () => {
    expect(describeStretch(2_140)).toBe('2.1 s');
    expect(describeStretch(42_000)).toBe('42 s');
  });

  it('counts a stretch over a minute in minutes and seconds', () => {
    expect(describeStretch(125_000)).toBe('2m 05s');
  });

  it('counts a stretch over an hour in hours and minutes', () => {
    expect(describeStretch(3_900_000)).toBe('1h 05m');
  });
});
