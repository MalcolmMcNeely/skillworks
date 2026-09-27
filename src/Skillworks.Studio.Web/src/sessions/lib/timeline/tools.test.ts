import { describe, expect, it } from 'vitest';
import { marksOf, type Step } from '../steps';
import { toolRowsOf } from './tools';

function step(id: string, clock: string, fields: Partial<Step> = {}): Step {
  return {
    id,
    kind: 'tool',
    atUtc: `2026-09-14T${clock}.000Z`,
    lengthMs: 0,
    tool: 'Bash',
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

describe('toolRowsOf', () => {
  it('gives each tool one row with its calls and the summed length of them', () => {
    const rows = toolRowsOf(
      marksOf([
        step('1', '09:00:00', { lengthMs: 2_000 }),
        step('2', '09:00:10', { lengthMs: 3_000 }),
        step('3', '09:00:20', { tool: 'Read', lengthMs: 500 }),
      ]),
      null,
    );

    expect(rows).toEqual([
      { tool: 'Bash', calls: 2, faults: 0, friction: 0, lengthMs: 5_000 },
      { tool: 'Read', calls: 1, faults: 0, friction: 0, lengthMs: 500 },
    ]);
  });

  it('counts Faults and Friction apart, so Friction never reads as a Fault', () => {
    const [row] = toolRowsOf(
      marksOf([
        step('1', '09:00:00', { fault: true }),
        step('2', '09:00:10', { kind: 'refused' }),
        step('3', '09:00:20', { kind: 'refused' }),
        step('4', '09:00:30'),
      ]),
      null,
    );

    expect(row).toEqual({ tool: 'Bash', calls: 4, faults: 1, friction: 2, lengthMs: 0 });
  });

  it('puts the tool with the most calls first, and breaks a tie by name', () => {
    const rows = toolRowsOf(
      marksOf([
        step('1', '09:00:00', { tool: 'Read' }),
        step('2', '09:00:10', { tool: 'Grep' }),
        step('3', '09:00:20', { tool: 'Edit' }),
        step('4', '09:00:30', { tool: 'Edit' }),
      ]),
      null,
    );

    expect(rows.map((row) => row.tool)).toEqual(['Edit', 'Grep', 'Read']);
  });

  it('leaves out every Step that is not a Tool call', () => {
    const rows = toolRowsOf(
      marksOf([
        step('1', '09:00:00', { kind: 'prompt', tool: null }),
        step('2', '09:00:10', { kind: 'turn', tool: null }),
        step('3', '09:00:20', { kind: 'fault', tool: null, fault: true }),
        step('4', '09:00:30'),
      ]),
      null,
    );

    expect(rows).toEqual([{ tool: 'Bash', calls: 1, faults: 0, friction: 0, lengthMs: 0 }]);
  });

  it('reads the View alone', () => {
    const rows = toolRowsOf(
      marksOf([step('1', '09:00:00'), step('2', '09:10:00', { tool: 'Read' })]),
      [at('09:05:00'), at('09:15:00')],
    );

    expect(rows.map((row) => row.tool)).toEqual(['Read']);
  });

  it('gives a View with no Tool call no rows', () => {
    expect(toolRowsOf([], null)).toEqual([]);
  });
});
