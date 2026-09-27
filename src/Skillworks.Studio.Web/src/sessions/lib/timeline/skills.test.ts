import { describe, expect, it } from 'vitest';
import { marksOf, type Step } from '../steps';
import { activationSpellsOf, type Activation } from './activations';
import { costIn, skillRowsOf } from './skills';

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

function fired(id: string, skill: string, clock: string): Activation {
  return { id, skill, atUtc: `2026-09-14T${clock}.000Z`, followedMs: 0, trigger: 'user-slash' };
}

const at = (clock: string) => Date.parse(`2026-09-14T${clock}.000Z`);

const bash = { kind: 'tool', tool: 'Bash' } as const;

describe('skillRowsOf', () => {
  it('gives each skill one row with its Turns, its Tool calls, its Cost and the summed length of its Steps', () => {
    const rows = skillRowsOf(
      marksOf([
        step('1', '09:00:00', { skill: 'tdd', cost: 0.25, lengthMs: 2_000 }),
        step('2', '09:00:10', { ...bash, skill: 'tdd', lengthMs: 500 }),
        step('3', '09:00:20', { ...bash, kind: 'refused', skill: 'tdd' }),
        step('4', '09:00:30', { skill: 'tdd', cost: 0.5, lengthMs: 1_000 }),
      ]),
      activationSpellsOf([fired('a', 'tdd', '08:59:59')]),
      null,
    );

    expect(rows).toEqual([
      { key: { kind: 'skill', name: 'tdd' }, label: 'tdd', fired: 1, turns: 2, toolCalls: 2, cost: 0.75, lengthMs: 3_500 },
    ]);
  });

  it('sets No skill and Unnamed spend apart from each other and after every named skill', () => {
    const rows = skillRowsOf(
      marksOf([
        step('1', '09:00:00', { unnamed: true, cost: 3 }),
        step('2', '09:00:10', { cost: 2 }),
        step('3', '09:00:20', { skill: 'tdd', cost: 0.1 }),
      ]),
      [],
      null,
    );

    expect(rows.map((row) => [row.label, row.fired])).toEqual([
      ['tdd', 0],
      ['No skill', null],
      ['Unnamed spend', null],
    ]);
  });

  it('adds up to the Cost in the View, No skill and Unnamed spend included', () => {
    const marks = marksOf([
      step('1', '09:00:00', { skill: 'implement', cost: 0.4 }),
      step('2', '09:00:10', { ...bash, kind: 'tool', skill: 'implement' }),
      step('3', '09:01:00', { skill: 'tdd', cost: 0.3 }),
      step('4', '09:02:00', { cost: 0.2 }),
      step('5', '09:03:00', { unnamed: true, cost: 0.1 }),
      step('6', '09:10:00', { skill: 'tdd', cost: 9 }),
    ]);
    const view: [number, number] = [at('08:59:00'), at('09:05:00')];

    const rows = skillRowsOf(marks, [], view);

    expect(rows.reduce((sum, row) => sum + row.cost, 0)).toBeCloseTo(costIn(marks, view));
    expect(costIn(marks, view)).toBeCloseTo(1);
  });

  it('counts a skill that called another apart from the skill it called', () => {
    const rows = skillRowsOf(
      marksOf([
        step('1', '09:00:00', { skill: 'implement', cost: 1 }),
        step('2', '09:00:10', { skill: 'tdd', cost: 2 }),
        step('3', '09:00:20', { ...bash, kind: 'tool', skill: 'tdd' }),
        step('4', '09:00:30', { skill: 'implement', cost: 1 }),
      ]),
      activationSpellsOf([fired('a', 'implement', '08:59:59'), fired('b', 'tdd', '09:00:05')]),
      null,
    );

    expect(rows.map((row) => [row.label, row.turns, row.toolCalls, row.cost])).toEqual([
      ['implement', 2, 0, 2],
      ['tdd', 1, 1, 2],
    ]);
  });

  it('leaves out Prompts, Answers and model Faults, as none of them is spend', () => {
    const rows = skillRowsOf(
      marksOf([
        step('1', '09:00:00', { kind: 'prompt' }),
        step('2', '09:00:10', { kind: 'answer' }),
        step('3', '09:00:20', { kind: 'fault', fault: true }),
      ]),
      [],
      null,
    );

    expect(rows).toEqual([]);
  });

  it('counts the times a skill fired in the View alone', () => {
    const rows = skillRowsOf(
      marksOf([step('1', '09:06:00', { skill: 'tdd' })]),
      activationSpellsOf([fired('a', 'tdd', '09:00:00'), fired('b', 'tdd', '09:06:00')]),
      [at('09:05:00'), at('09:10:00')],
    );

    expect(rows[0].fired).toBe(1);
  });

  it('reads Tool calls as not known in a Session with no Spans, and puts no call under No skill', () => {
    const rows = skillRowsOf(
      marksOf([
        step('1', '09:00:00', { skill: 'tdd', cost: 0.25, lengthMs: 2_000 }),
        step('2', '09:00:10', { ...bash, skillKnown: false, lengthMs: 500 }),
        step('3', '09:00:20', { ...bash, kind: 'refused', skillKnown: false }),
        step('4', '09:00:30', { cost: 0.5, lengthMs: 1_000 }),
      ]),
      [],
      null,
    );

    expect(rows).toEqual([
      { key: { kind: 'skill', name: 'tdd' }, label: 'tdd', fired: 0, turns: 1, toolCalls: null, cost: 0.25, lengthMs: 2_000 },
      { key: { kind: 'noSkill' }, label: 'No skill', fired: null, turns: 1, toolCalls: null, cost: 0.5, lengthMs: 1_000 },
    ]);
  });

  it('adds up to the Cost in the View in a Session with no Spans', () => {
    const marks = marksOf([
      step('1', '09:00:00', { skill: 'implement', cost: 0.4 }),
      step('2', '09:00:10', { ...bash, skillKnown: false }),
      step('3', '09:01:00', { skill: 'tdd', cost: 0.3 }),
      step('4', '09:02:00', { cost: 0.2 }),
      step('5', '09:03:00', { unnamed: true, cost: 0.1 }),
      step('6', '09:10:00', { skill: 'tdd', cost: 9 }),
    ]);
    const view: [number, number] = [at('08:59:00'), at('09:05:00')];

    const rows = skillRowsOf(marks, [], view);

    expect(rows.reduce((sum, row) => sum + row.cost, 0)).toBeCloseTo(costIn(marks, view));
    expect(costIn(marks, view)).toBeCloseTo(1);
  });

  it('gives no row to a skill that fired but has no Step in the View', () => {
    expect(skillRowsOf([], activationSpellsOf([fired('a', 'tdd', '09:00:00')]), null)).toEqual([]);
  });
});
