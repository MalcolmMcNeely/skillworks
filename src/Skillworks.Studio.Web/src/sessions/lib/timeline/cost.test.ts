import { describe, expect, it } from 'vitest';
import { marksOf, type Step } from '../steps';
import { ranByOne } from './agents';
import type { StepDetails, TurnDetails } from '../details';
import { moneyTicksOf, nearestTurnOf, purposeWordsOf, skillWordsOf, turnsOf } from './cost';
import type { Spell } from './view';

function step(id: string, clock: string, fields: Partial<Step> = {}): Step {
  return {
    id,
    kind: 'turn',
    atUtc: `2026-09-14T${clock}.000Z`,
    lengthMs: 0,
    tool: null,
    fault: false,
    words: null,
    skill: null,
    unnamed: false,
    skillKnown: true,
    cost: 0,
    ...fields,
  };
}

function turned(turn: Partial<TurnDetails>): StepDetails {
  return {
    turns: {
      '1': {
        purpose: 'work',
        side: null,
        sentAs: null,
        model: 'claude-opus-5',
        effort: null,
        speed: null,
        cost: 0,
        lengthMs: 0,
        firstWordMs: null,
        cacheReadTokens: 0,
        cacheWriteTokens: 0,
        inputTokens: 0,
        outputTokens: 0,
        words: null,
        wordsLength: null,
        stopReason: null,
        attempt: null,
        ...turn,
      },
    },
    tools: {},
    refusals: {},
    faults: {},
  };
}

const at = (clock: string) => Date.parse(`2026-09-14T${clock}.000Z`);

describe('turnsOf', () => {
  it('counts from nought the Turns a View cuts into, in the order they ended', () => {
    const marks = marksOf([
      step('before', '09:00:00', { lengthMs: 10_000, cost: 5 }),
      step('cut', '09:01:50', { lengthMs: 20_000, cost: 0.25 }),
      step('long', '09:02:00', { lengthMs: 60_000, cost: 0.5 }),
      step('call', '09:02:10', { kind: 'tool', tool: 'Bash', lengthMs: 1_000 }),
      step('short', '09:02:20', { lengthMs: 5_000, cost: 0.125 }),
      step('after', '09:10:00', { lengthMs: 1_000, cost: 7 }),
    ]);
    const view: Spell = [at('09:02:00'), at('09:05:00')];

    const turns = turnsOf(marks, view);

    expect(turns.map((turn) => [turn.mark.step.id, turn.soFar])).toEqual([
      ['cut', 0.25],
      ['short', 0.375],
      ['long', 0.875],
    ]);
  });

  it('ends at the Session Cost with no View', () => {
    const marks = marksOf([
      step('1', '09:00:00', { lengthMs: 1_000, cost: 0.5 }),
      step('2', '10:00:00', { lengthMs: 1_000, cost: 1.25 }),
      step('3', '11:00:00', { lengthMs: 1_000, cost: 2 }),
    ]);

    const turns = turnsOf(marks, null);

    expect(turns.at(-1)?.soFar).toBe(3.75);
  });

  it('counts nothing in a run that made no Turn', () => {
    const marks = marksOf([
      step('prompt', '09:00:00', { kind: 'prompt' }),
      step('call', '09:00:10', { kind: 'tool', tool: 'Read', lengthMs: 100 }),
    ]);

    expect(turnsOf(marks, null)).toEqual([]);
  });

  it('counts the Turns of an open Subagent alone', () => {
    const marks = marksOf([
      step('main', '09:00:00', { lengthMs: 1_000, cost: 4 }),
      step('sub-1', '09:00:10', { lengthMs: 1_000, cost: 0.5 }),
      step('sub-2', '09:00:20', { lengthMs: 1_000, cost: 0.25 }),
    ]);
    const drawn = ranByOne(marks, { 'sub-1': 'Explore', 'sub-2': 'Explore' }, 'Explore');

    const turns = turnsOf(drawn, null);

    expect(turns.map((turn) => [turn.mark.step.id, turn.soFar])).toEqual([
      ['sub-1', 0.5],
      ['sub-2', 0.75],
    ]);
  });
});

describe('nearestTurnOf', () => {
  it('finds the Turn whose end lies nearest a point, not the one whose start does', () => {
    const turns = turnsOf(
      marksOf([
        step('long', '09:00:00', { lengthMs: 50_000, cost: 1 }),
        step('short', '09:01:00', { lengthMs: 10_000, cost: 1 }),
      ]),
      null,
    );

    expect(nearestTurnOf(turns, at('09:00:45'))?.mark.step.id).toBe('long');
  });
});

describe('skillWordsOf', () => {
  it('words a Turn of Unnamed spend as the Skills tab does', () => {
    expect(skillWordsOf(step('turn', '09:00:00', { skill: 'grill', unnamed: true }))).toBe('Unnamed spend');
  });

  it('words a Turn of No skill as the Skills tab does', () => {
    expect(skillWordsOf(step('turn', '09:00:00'))).toBe('No skill');
  });
});

describe('purposeWordsOf', () => {
  it('says a Turn sent for the Prompt was work on it', () => {
    expect(purposeWordsOf(step('1', '09:00:00'), turned({}))).toBe('Why it ran: Work on the Prompt');
  });

  it('names a Side request in words', () => {
    expect(purposeWordsOf(step('1', '09:00:00'), turned({ purpose: 'side', side: 'awaySummary' }))).toBe(
      'Why it ran: Recap while you were away',
    );
  });

  it('says nothing more until the details arrive', () => {
    expect(purposeWordsOf(step('1', '09:00:00'), null)).toBeNull();
  });
});

describe('moneyTicksOf', () => {
  it('marks the money axis in round ticks that pass a total falling on one', () => {
    expect(moneyTicksOf(2)).toEqual([0, 1, 2, 3]);
  });
});
