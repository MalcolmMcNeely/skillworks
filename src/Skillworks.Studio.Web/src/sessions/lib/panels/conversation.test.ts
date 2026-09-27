import { describe, expect, it } from 'vitest';
import { bandsOf, type Exchange } from './conversation';

function exchange(fields: Partial<Exchange> & Pick<Exchange, 'index' | 'atUtc'>): Exchange {
  return {
    lengthMs: 0,
    prompt: null,
    promptLength: 0,
    answer: null,
    answerLength: 0,
    turns: 0,
    toolCalls: 0,
    cost: 0,
    ...fields,
  };
}

describe('bandsOf', () => {
  it('places an exchange by when it opened and how long it ran', () => {
    const [band] = bandsOf([exchange({ index: 0, atUtc: '2026-09-14T09:00:00.000Z', lengthMs: 10_000 })]);

    expect(band.startMs).toBe(Date.parse('2026-09-14T09:00:00.000Z'));
    expect(band.endMs).toBe(Date.parse('2026-09-14T09:00:10.000Z'));
  });

  it('keeps the exchange itself, so a band and the block beneath it read the same figures', () => {
    const said = exchange({ index: 2, atUtc: '2026-09-14T09:00:00.000Z', turns: 3 });

    expect(bandsOf([said])[0].exchange).toBe(said);
  });

  it('draws nothing for a run nobody typed into', () => {
    expect(bandsOf([])).toEqual([]);
  });
});
