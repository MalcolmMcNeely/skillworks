import { describe, expect, it } from 'vitest';
import { activationSpellsOf, tallyOf, type Activation } from './activations';

function activation(id: string, skill: string, atUtc: string, followedMs: number): Activation {
  return { id, skill, atUtc, followedMs, trigger: 'user-slash' };
}

const at = (clock: string) => Date.parse(`2026-09-14T${clock}.000Z`);

const implement = activation('1', 'implement', '2026-09-14T09:00:00.000Z', 300_000);

const tdd = activation('2', 'tdd', '2026-09-14T09:05:00.000Z', 600_000);

describe('activationSpellsOf', () => {
  it('runs an activation from when the skill fired to the end of what followed it', () => {
    const [spell] = activationSpellsOf([implement]);

    expect(spell.atMs).toBe(at('09:00:00'));
    expect(spell.followedToMs).toBe(at('09:05:00'));
  });

  it('keeps the order the answer gave', () => {
    expect(activationSpellsOf([implement, tdd]).map((spell) => spell.activation.skill)).toEqual(['implement', 'tdd']);
  });

  it('gives a run no activation when no skill fired', () => {
    expect(activationSpellsOf([])).toEqual([]);
  });
});

describe('tallyOf', () => {
  it('counts one skill that fired twice as one skill and two activations', () => {
    const twice = activationSpellsOf([
      activation('1', 'tdd', '2026-09-14T09:00:00.000Z', 0),
      activation('2', 'tdd', '2026-09-14T09:05:00.000Z', 0),
    ]);

    expect(tallyOf(twice)).toEqual({ activations: 2, skills: 1 });
  });

  it('counts nothing for a stretch no skill fired in', () => {
    expect(tallyOf([])).toEqual({ activations: 0, skills: 0 });
  });
});
