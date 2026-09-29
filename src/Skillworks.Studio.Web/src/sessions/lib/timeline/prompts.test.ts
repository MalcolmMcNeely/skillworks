import { describe, expect, it } from 'vitest';
import { bandsOf, type Exchange } from './conversation';
import { readHighlight } from './highlight';
import { closedPrompts, describeUnsaid, exchangeOf, promptsOf, type Opened, type PromptRow } from './prompts';
import { readView } from './view';
import { marksOf, type Step } from '../steps';

function exchange(index: number, atUtc: string): Exchange {
  return {
    index,
    atUtc,
    lengthMs: 60_000,
    prompt: null,
    promptLength: 0,
    answer: null,
    answerLength: 0,
    turns: 0,
    toolCalls: 0,
    cost: 0,
    subagents: null,
  };
}

function step(id: string, atUtc: string): Step {
  return {
    id,
    kind: 'tool',
    atUtc,
    lengthMs: 0,
    tool: 'Bash',
    fault: false,
    words: null,
    skill: null,
    unnamed: false,
    skillKnown: true,
    cost: 0,
  };
}

const bands = bandsOf([exchange(0, '2026-09-14T09:00:00.000Z'), exchange(1, '2026-09-14T09:05:00.000Z')]);

function markAt(atUtc: string) {
  return marksOf([step('41', atUtc)])[0];
}

describe('exchangeOf', () => {
  it('puts a Step that starts with an Exchange in that Exchange', () => {
    expect(exchangeOf(markAt('2026-09-14T09:05:00.000Z'), bands)?.exchange.index).toBe(1);
  });

  it('puts a Step in the middle of an Exchange in that Exchange', () => {
    expect(exchangeOf(markAt('2026-09-14T09:02:30.000Z'), bands)?.exchange.index).toBe(0);
  });

  it('puts a Step from before the first Prompt in no Exchange', () => {
    expect(exchangeOf(markAt('2026-09-14T08:59:59.000Z'), bands)).toBeNull();
  });

  it('puts a Step after the last Exchange ended in the last Exchange', () => {
    expect(exchangeOf(markAt('2026-09-14T10:00:00.000Z'), bands)?.exchange.index).toBe(1);
  });
});

const nothingOpened = { step: null, exchange: null };

function keysOf(rows: readonly PromptRow[]): string[] {
  return rows.map((row) => (row.band === null ? 'before' : String(row.band.exchange.index)));
}

describe('promptsOf', () => {
  it('lists a run with Steps before the first Prompt with a Before the first Prompt row at the top', () => {
    const marks = marksOf([step('40', '2026-09-14T08:59:00.000Z'), step('41', '2026-09-14T09:01:00.000Z')]);

    expect(keysOf(promptsOf(marks, bands, nothingOpened))).toEqual(['before', '0', '1']);
  });

  it('lists a run with no Steps before the first Prompt with one row per Exchange and nothing more', () => {
    const marks = marksOf([step('41', '2026-09-14T09:01:00.000Z')]);

    expect(keysOf(promptsOf(marks, bands, nothingOpened))).toEqual(['0', '1']);
  });
});

describe('the open row', () => {
  const marks = marksOf([step('40', '2026-09-14T08:59:00.000Z'), step('41', '2026-09-14T09:06:00.000Z')]);

  function openOf(opened: Opened): string[] {
    return keysOf(promptsOf(marks, bands, opened).filter((row) => row.open));
  }

  it('is the Exchange a named Step sits in', () => {
    expect(openOf({ step: '41', exchange: null })).toEqual(['1']);
  });

  it('is the named Exchange where no Step is named', () => {
    expect(openOf({ step: null, exchange: 0 })).toEqual(['0']);
  });

  it('is the Exchange of the named Step where the address names an Exchange as well', () => {
    expect(openOf({ step: '41', exchange: 0 })).toEqual(['1']);
  });

  it('is the Before the first Prompt row for a Step from before the first Prompt', () => {
    expect(openOf({ step: '40', exchange: null })).toEqual(['before']);
  });

  it('is none where nothing is named', () => {
    expect(openOf(nothingOpened)).toEqual([]);
  });
});

describe('describeUnsaid', () => {
  it('says a withheld Prompt was withheld, and how many characters it held', () => {
    expect(describeUnsaid(null, 1234)).toBe('Withheld · 1,234 characters');
  });

  it('says nothing was recorded where there are no words and no length', () => {
    expect(describeUnsaid(null, 0)).toBe('Nothing was recorded');
  });

  it('says nothing where the words are there to read', () => {
    expect(describeUnsaid('Fix the build', 13)).toBeNull();
  });
});

describe('closedPrompts', () => {
  const address = new URLSearchParams('at=1000&until=2000&lit=tool%3ABash&step=41&exchange=1');

  it('clears the named Step and the named Exchange', () => {
    const closed = closedPrompts(address);

    expect([closed.has('step'), closed.has('exchange')]).toEqual([false, false]);
  });

  it('keeps the View and the Highlight', () => {
    const closed = closedPrompts(address);

    expect([readView(closed), readHighlight(closed)]).toEqual([[1000, 2000], { kind: 'tool', name: 'Bash' }]);
  });
});
