import { describe, expect, it } from 'vitest';
import { everything, type Filter } from './filters';
import { spanKeyOf, todayUtc, withSpanKey } from './spanKeys';

const narrowed: Filter = { from: '2026-09-01', to: '2026-09-05', repository: 'skillworks', skill: '' };

describe('withSpanKey', () => {
  it('narrows 24H to today alone, keeping the rest of the filter', () => {
    expect(withSpanKey(narrowed, '24h', '2026-09-15')).toEqual({ ...narrowed, from: '2026-09-15', to: '2026-09-15' });
  });

  it('writes both dates for 7D, as the lookback the API falls back to can be another length', () => {
    expect(withSpanKey(narrowed, '7d', '2026-09-15')).toEqual({ ...narrowed, from: '2026-09-09', to: '2026-09-15' });
  });

  it('narrows 30D to the thirty days that end today', () => {
    expect(withSpanKey(narrowed, '30d', '2026-09-15')).toEqual({ ...narrowed, from: '2026-08-17', to: '2026-09-15' });
  });

  it('counts the thirty days back across a short month', () => {
    expect(withSpanKey(everything, '30d', '2026-03-01')).toMatchObject({ from: '2026-01-31', to: '2026-03-01' });
  });
});

describe('spanKeyOf', () => {
  it('presses the key whose days the span covers, ending today', () => {
    expect(spanKeyOf({ from: '2026-09-15', to: '2026-09-15' }, '2026-09-15')).toBe('24h');
    expect(spanKeyOf({ from: '2026-09-09', to: '2026-09-15' }, '2026-09-15')).toBe('7d');
    expect(spanKeyOf({ from: '2026-08-17', to: '2026-09-15' }, '2026-09-15')).toBe('30d');
  });

  it('presses no key for a lookback of another length', () => {
    expect(spanKeyOf({ from: '2026-09-02', to: '2026-09-15' }, '2026-09-15')).toBeNull();
  });

  it('presses no key for a span from an older link, which still opens the days it names', () => {
    expect(spanKeyOf(narrowed, '2026-09-15')).toBeNull();
    expect(spanKeyOf({ from: '2026-09-15', to: '' }, '2026-09-15')).toBeNull();
  });
});

describe('todayUtc', () => {
  it('names the UTC day, which the span keys count in, not the local one', () => {
    expect(todayUtc(new Date('2026-09-15T23:30:00-05:00'))).toBe('2026-09-16');
  });
});
