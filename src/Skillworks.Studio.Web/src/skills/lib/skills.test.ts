import { describe, expect, it } from 'vitest';
import {
  ariaSort,
  describeList,
  describeMoney,
  describeSplit,
  describeUnnamedSpend,
  sortMark,
  type TurnTotals,
} from './skills';

const spend: TurnTotals = {
  inputTokens: 1500,
  outputTokens: 6000,
  cacheReadTokens: 3000000,
  cacheCreationTokens: 400000,
  cost: 0.3,
};

describe('describeList', () => {
  it('joins the values it was given', () => {
    expect(describeList(['high', 'medium'])).toBe('high, medium');
  });

  it('shows a dash when there is nothing to list', () => {
    expect(describeList([])).toBe('—');
  });

  it('says not named, not a dash, when Claude Code did not name the skill on its Turns', () => {
    expect(describeList(null)).toBe('Not named');
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

  it('says not named, never $0.00, when Claude Code did not name the skill on its Turns', () => {
    expect(describeMoney(null)).toBe('Not named');
  });
});

describe('describeSplit', () => {
  it('names each kind of token Claude Code reports, so a long skill and a cache buster read differently', () => {
    expect(describeSplit(spend)).toBe('in 1,500 · out 6,000 · cache read 3,000,000 · cache creation 400,000');
  });

  it('says not named, never zero tokens, when Claude Code did not name the skill on its Turns', () => {
    expect(describeSplit(null)).toBe('Not named');
  });
});

describe('describeUnnamedSpend', () => {
  it('shows unnamed spend as one amount of its own, with its cost and each kind of token', () => {
    expect(describeUnnamedSpend(spend)).toBe(
      'Unnamed spend: $0.30 · in 1,500 · out 6,000 · cache read 3,000,000 · cache creation 400,000. ' +
        'Claude Code does not name a skill from a plugin outside Anthropic’s marketplaces, so this spend is in no skill’s cost.',
    );
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
