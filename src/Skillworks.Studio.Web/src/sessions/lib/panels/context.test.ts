import { describe, expect, it } from 'vitest';
import { ceilingOf, describeInForce, inForceBands, levelsOf, tallyOf, type ContextPoint } from './context';

function point(id: string, atUtc: string, tokens: number, held: Partial<ContextPoint> = {}): ContextPoint {
  return {
    id,
    atUtc,
    lengthMs: 2_000,
    tokens,
    writtenToCache: 0,
    skill: null,
    unnamed: false,
    rebuilt: false,
    ...held,
  };
}

const at = (clock: string) => Date.parse(`2026-09-14T${clock}.000Z`);

describe('levelsOf', () => {
  it('runs a level across the turn it stands for', () => {
    const [level] = levelsOf([point('1', '2026-09-14T09:00:00.000Z', 40_000)]);

    expect(level.startMs).toBe(at('09:00:00'));
    expect(level.endMs).toBe(at('09:00:02'));
  });

  it('keeps the order the answer gave', () => {
    const points = [point('1', '2026-09-14T09:00:00.000Z', 40_000), point('2', '2026-09-14T09:05:00.000Z', 90_000)];

    expect(levelsOf(points).map((level) => level.point.tokens)).toEqual([40_000, 90_000]);
  });

  it('gives a run with no turn no level', () => {
    expect(levelsOf([])).toEqual([]);
  });
});

describe('describeInForce', () => {
  it('names the skill in force on a turn', () => {
    expect(describeInForce(point('1', '2026-09-14T09:00:00.000Z', 10, { skill: 'tdd' }))).toBe('tdd');
  });

  it('says a turn had no skill rather than guessing one', () => {
    expect(describeInForce(point('1', '2026-09-14T09:00:00.000Z', 10))).toBe('None');
  });

  it('says a skill was in force but not named apart from one that had none', () => {
    expect(describeInForce(point('1', '2026-09-14T09:00:00.000Z', 10, { unnamed: true }))).toBe('Not named');
  });
});

describe('tallyOf', () => {
  const levels = levelsOf([
    point('1', '2026-09-14T09:00:00.000Z', 40_000),
    point('2', '2026-09-14T09:05:00.000Z', 420_000, { rebuilt: true }),
    point('3', '2026-09-14T09:10:00.000Z', 90_000),
  ]);

  it('counts the turns, the peak and the cache rebuilds', () => {
    expect(tallyOf(levels, 1_000_000)).toEqual({ turns: 3, peakTokens: 420_000, peakShare: 0.42, rebuilds: 1 });
  });

  it('gives no share where no limit is known', () => {
    expect(tallyOf(levels, null).peakShare).toBeNull();
  });

  it('counts nothing for a View with no turn in it', () => {
    expect(tallyOf([], 1_000_000)).toEqual({ turns: 0, peakTokens: 0, peakShare: null, rebuilds: 0 });
  });

  it('gives a View with no turn no share, so an empty View never reads as nought percent', () => {
    expect(tallyOf([], 1_000_000).peakShare).toBeNull();
  });
});

describe('ceilingOf', () => {
  const levels = levelsOf([point('1', '2026-09-14T09:00:00.000Z', 40_000)]);

  it('draws the series against the limit, so the headroom left is what the reader sees', () => {
    expect(ceilingOf(levels, 1_000_000)).toBe(1_000_000);
  });

  it('draws the series against its own peak where no limit is known', () => {
    expect(ceilingOf(levels, null)).toBe(40_000);
  });

  it('rises above a limit a turn passed, so the bar that broke it is still drawn whole', () => {
    const past = levelsOf([point('1', '2026-09-14T09:00:00.000Z', 250_000)]);

    expect(ceilingOf(past, 200_000)).toBe(250_000);
  });

  it('never divides by nothing when a View holds no turn', () => {
    expect(ceilingOf([], null)).toBe(1);
  });
});

describe('inForceBands', () => {
  it('runs turns under one skill into one band', () => {
    const levels = levelsOf([
      point('1', '2026-09-14T09:00:00.000Z', 10, { skill: 'tdd' }),
      point('2', '2026-09-14T09:01:00.000Z', 10, { skill: 'tdd' }),
      point('3', '2026-09-14T09:02:00.000Z', 10, { skill: 'implement' }),
    ]);

    expect(inForceBands(levels)).toEqual([
      { label: 'tdd', from: 0, to: 1 },
      { label: 'implement', from: 2, to: 2 },
    ]);
  });

  it('breaks a band where the same skill comes back after another', () => {
    const levels = levelsOf([
      point('1', '2026-09-14T09:00:00.000Z', 10, { skill: 'tdd' }),
      point('2', '2026-09-14T09:01:00.000Z', 10, { skill: 'implement' }),
      point('3', '2026-09-14T09:02:00.000Z', 10, { skill: 'tdd' }),
    ]);

    expect(inForceBands(levels).map((band) => band.label)).toEqual(['tdd', 'implement', 'tdd']);
  });

  it('bands the turns that had no skill too', () => {
    const levels = levelsOf([point('1', '2026-09-14T09:00:00.000Z', 10)]);

    expect(inForceBands(levels)).toEqual([{ label: 'None', from: 0, to: 0 }]);
  });

  it('gives a View with no turn no band', () => {
    expect(inForceBands([])).toEqual([]);
  });
});
