import { describe, expect, it } from 'vitest';
import { firingsOf, tallyOf, type SkillCall } from './skillCalls';

function call(id: string, skill: string, atUtc: string, followedMs: number): SkillCall {
  return { id, skill, atUtc, followedMs, trigger: 'user-slash' };
}

const at = (clock: string) => Date.parse(`2026-09-14T${clock}.000Z`);

const implement = call('1', 'implement', '2026-09-14T09:00:00.000Z', 300_000);

const tdd = call('2', 'tdd', '2026-09-14T09:05:00.000Z', 600_000);

describe('firingsOf', () => {
  it('runs a firing from when the skill fired to the end of what followed it', () => {
    const [firing] = firingsOf([implement]);

    expect(firing.atMs).toBe(at('09:00:00'));
    expect(firing.followedToMs).toBe(at('09:05:00'));
  });

  it('keeps the order the answer gave', () => {
    expect(firingsOf([implement, tdd]).map((firing) => firing.call.skill)).toEqual(['implement', 'tdd']);
  });

  it('gives a run no firing when no skill fired', () => {
    expect(firingsOf([])).toEqual([]);
  });
});

describe('tallyOf', () => {
  it('counts one skill that fired twice as one skill and two calls', () => {
    const twice = firingsOf([call('1', 'tdd', '2026-09-14T09:00:00.000Z', 0), call('2', 'tdd', '2026-09-14T09:05:00.000Z', 0)]);

    expect(tallyOf(twice)).toEqual({ calls: 2, skills: 1 });
  });

  it('counts nothing for a stretch no skill fired in', () => {
    expect(tallyOf([])).toEqual({ calls: 0, skills: 0 });
  });
});
