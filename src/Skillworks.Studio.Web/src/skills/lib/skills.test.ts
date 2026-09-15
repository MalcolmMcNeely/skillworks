import { describe, expect, it } from 'vitest';
import { ariaSort, describeList, describeMoney, describeSplit, sortMark, type TokenSplit } from './skills';

const spend: TokenSplit = {
  inputTokens: 1500,
  outputTokens: 6000,
  cacheReadTokens: 3000000,
  cacheCreationTokens: 400000,
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
});

describe('describeSplit', () => {
  it('names each kind of token Claude Code reports, so a long skill and a cache buster read differently', () => {
    expect(describeSplit(spend)).toBe('in 1,500 · out 6,000 · cache read 3,000,000 · cache creation 400,000');
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
