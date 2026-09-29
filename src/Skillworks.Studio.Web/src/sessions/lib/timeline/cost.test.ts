import { describe, expect, it } from 'vitest';
import { marksOf, type Step } from '../steps';
import { ranByOne } from './agents';
import { moneyTicksOf, turnsOf } from './cost';
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

describe('moneyTicksOf', () => {
  it('marks the money axis in round ticks that pass a total falling on one', () => {
    expect(moneyTicksOf(2)).toEqual([0, 1, 2, 3]);
  });
});
