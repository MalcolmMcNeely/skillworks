import { describe, expect, it } from 'vitest';
import { bandsOf, describeWithheld, figuresOf, type Exchange } from './conversation';

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

describe('figuresOf', () => {
  const bands = bandsOf([
    exchange({ index: 0, atUtc: '2026-09-14T09:00:00.000Z', turns: 2, toolCalls: 5, cost: 0.4 }),
    exchange({ index: 1, atUtc: '2026-09-14T09:05:00.000Z', turns: 3, toolCalls: 1, cost: 0.1 }),
  ]);

  it('counts the exchanges, the turns, the tool calls and the cost it was given', () => {
    expect(figuresOf(bands)).toEqual({ exchanges: 2, turns: 5, toolCalls: 6, cost: 0.5 });
  });

  it('counts the View alone, so the figures answer the question the reader asked', () => {
    expect(figuresOf(bands.slice(1))).toEqual({ exchanges: 1, turns: 3, toolCalls: 1, cost: 0.1 });
  });

  it('counts an empty View as nothing rather than as nothing known', () => {
    expect(figuresOf([])).toEqual({ exchanges: 0, turns: 0, toolCalls: 0, cost: 0 });
  });
});

describe('describeWithheld', () => {
  it('says how much was said where the words themselves cannot be read', () => {
    expect(describeWithheld(1_840)).toBe('Withheld · 1,840 characters');
  });
});
