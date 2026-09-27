import { describe, expect, it } from 'vitest';
import { namedIn, type Finding } from './findings';
import { momentOf, mostFaults } from './moment';
import { marksOf, type Step } from '../steps';

const at = (clock: string) => Date.parse(`2026-09-14T${clock}.000Z`);

function step(id: string, clock: string, fields: Partial<Step> = {}): Step {
  return {
    id,
    kind: 'tool',
    atUtc: `2026-09-14T${clock}.000Z`,
    lengthMs: 1_000,
    tool: 'Bash',
    fault: false,
    words: null,
    skill: null,
    unnamed: false,
    cost: 0,
    ...fields,
  };
}

const finding: Finding = {
  kind: 'failingAgain',
  subject: 'npm test',
  figure: 4,
  bar: 3,
  step: '3',
  atUtc: '2026-09-14T10:00:00.000Z',
  lengthMs: 60_000,
};

const [named] = namedIn({ kind: 'findings', findings: [finding] });

const whole: [number, number] = [at('09:00:00'), at('11:00:00')];

describe('momentOf', () => {
  it('pads the moment a finding happened in, so its steps never sit flush against the edge', () => {
    const { spell } = momentOf(named, [], whole);

    expect(spell[0]).toBeLessThan(named.startMs);
    expect(spell[1]).toBeGreaterThan(named.endMs);
  });

  it('keeps the moment inside the run', () => {
    const early = namedIn({ kind: 'findings', findings: [{ ...finding, atUtc: '2026-09-14T09:00:00.000Z' }] })[0];

    expect(momentOf(early, [], whole).spell[0]).toBe(whole[0]);
  });

  it('holds the steps around the moment and none from far away', () => {
    const marks = marksOf([step('1', '09:10:00'), step('2', '10:00:10'), step('3', '10:00:30')]);

    expect(momentOf(named, marks, whole).marks.map((mark) => mark.step.id)).toEqual(['2', '3']);
  });

  it('lists the faults from the moment, and none of the calls that went well', () => {
    const marks = marksOf([
      step('1', '10:00:05', { fault: true }),
      step('2', '10:00:10'),
      step('3', '10:00:20', { kind: 'refused' }),
      step('4', '10:00:40', { kind: 'fault', tool: null, fault: true }),
    ]);

    expect(momentOf(named, marks, whole).faults.map((mark) => mark.step.id)).toEqual(['1', '4']);
  });

  it('lists the first five faults and no more, in the order they happened', () => {
    const clocks = ['10:00:50', '10:00:10', '10:00:20', '10:00:30', '10:00:40', '10:00:05', '10:00:45'];
    const marks = marksOf(clocks.map((clock, place) => step(String(place), clock, { fault: true })));

    const faults = momentOf(named, marks, whole).faults;

    expect(faults).toHaveLength(mostFaults);
    expect(faults.map((mark) => mark.step.id)).toEqual(['5', '1', '2', '3', '4']);
  });
});
