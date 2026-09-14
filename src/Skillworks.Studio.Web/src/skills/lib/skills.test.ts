import { describe, expect, it } from 'vitest';
import { ariaSort, describeList, describeMoney, describeSplit, sortMark, type TokenSplit } from './skills';

const spend: TokenSplit = {
  inputTokens: 1500,
  outputTokens: 6000,
  cacheReadTokens: 3000000,
  cacheWriteTokens: 400000,
};

describe('describeList', () => {
  it('joins the values it was given', () => {
    expect(describeList(['alpha', 'beta'])).toBe('alpha, beta');
  });

  it('shows a dash when a skill has never fired anywhere', () => {
    expect(describeList([])).toBe('—');
  });
});

describe('describeMoney', () => {
  it('shows the pennies', () => {
    expect(describeMoney(14.5215)).toBe('$14.5215');
    expect(describeMoney(0)).toBe('$0.00');
  });

  it('keeps a fraction of a penny rather than rounding it away to free', () => {
    expect(describeMoney(0.0022)).toBe('$0.0022');
  });

  it('marks a cost the API could only partly work out', () => {
    expect(describeMoney(1.5, true)).toBe('$1.50+');
  });
});

describe('describeSplit', () => {
  it('names each kind of token so a long skill and a cache buster read differently', () => {
    expect(describeSplit(spend)).toBe('in 1,500 · out 6,000 · cache 3,000,000r · 400,000w');
  });

  it('leaves the thinking out, because it is already inside the output', () => {
    expect(describeSplit(spend)).not.toContain('think');
  });
});

describe('sortMark', () => {
  it('points up when the column sorts ascending', () => {
    expect(sortMark('asc')).toBe(' ▲');
  });

  it('points down when the column sorts descending', () => {
    expect(sortMark('desc')).toBe(' ▼');
  });

  it('marks nothing when the column is not sorted', () => {
    expect(sortMark(false)).toBe('');
  });
});

describe('ariaSort', () => {
  it('names the direction a sorted column runs in', () => {
    expect(ariaSort('asc')).toBe('ascending');
    expect(ariaSort('desc')).toBe('descending');
  });

  it('says none when the column is not sorted', () => {
    expect(ariaSort(false)).toBe('none');
  });
});
