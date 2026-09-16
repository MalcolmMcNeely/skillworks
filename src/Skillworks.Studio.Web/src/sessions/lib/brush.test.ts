import { describe, expect, it } from 'vitest';
import { clamp, holds, inRange, moved, rangeOf, readRange, widened, withRange } from './brush';
import type { Range } from './steps';

const whole: Range = [1_000, 101_000];

describe('rangeOf', () => {
  it('puts the two ends in order, so a brush dragged backwards still holds a stretch', () => {
    expect(rangeOf(60_000, 20_000, whole)).toEqual([20_000, 60_000]);
  });

  it('holds both ends inside the run, so a brush dragged off the edge stops at it', () => {
    expect(rangeOf(-5_000, 500_000, whole)).toEqual(whole);
  });
});

describe('widened', () => {
  it('pads around a stretch, so the step a reader asked for is not flush against the edge', () => {
    const [from, to] = widened([50_000, 51_000], whole, 5_000);

    expect(from).toBe(45_000);
    expect(to).toBe(56_000);
  });

  it('pads a long stretch by a share of itself rather than by the least', () => {
    const [from, to] = widened([100_000, 200_000], [0, 400_000], 1_000);

    expect(from).toBe(100_000 - 8_000);
    expect(to).toBe(200_000 + 8_000);
  });

  it('never pads past the ends of the run', () => {
    expect(widened(whole, whole, 5_000)).toEqual(whole);
  });
});

describe('moved', () => {
  it('keeps the stretch the same length when the brush is dragged along', () => {
    expect(moved([20_000, 30_000], 5_000, whole)).toEqual([25_000, 35_000]);
  });

  it('stops at the end of the run rather than shrinking the stretch', () => {
    expect(moved([20_000, 30_000], 500_000, whole)).toEqual([91_000, 101_000]);
  });

  it('stops at the start of the run', () => {
    expect(moved([20_000, 30_000], -500_000, whole)).toEqual([1_000, 11_000]);
  });
});

describe('holds', () => {
  it('holds everything while no stretch is brushed, so every panel reads the whole run', () => {
    expect(holds(null, 0, 1)).toBe(true);
  });

  it('holds a step that overlaps the brushed stretch at either end', () => {
    expect(holds([20_000, 30_000], 15_000, 21_000)).toBe(true);
    expect(holds([20_000, 30_000], 29_000, 40_000)).toBe(true);
  });

  it('leaves out a step wholly before or after the brushed stretch', () => {
    expect(holds([20_000, 30_000], 5_000, 10_000)).toBe(false);
    expect(holds([20_000, 30_000], 40_000, 50_000)).toBe(false);
  });
});

describe('inRange', () => {
  const stretches = [
    { name: 'early', startMs: 5_000, endMs: 10_000 },
    { name: 'across', startMs: 15_000, endMs: 21_000 },
    { name: 'inside', startMs: 22_000, endMs: 28_000 },
    { name: 'late', startMs: 40_000, endMs: 50_000 },
  ];

  it('narrows to the stretches the brush holds, so a panel shows only what is in view', () => {
    expect(inRange(stretches, [20_000, 30_000]).map((each) => each.name)).toEqual(['across', 'inside']);
  });

  it('keeps everything while no stretch is brushed, so clearing the brush returns the whole run', () => {
    expect(inRange(stretches, null)).toHaveLength(4);
  });

  it('narrows to nothing where the brush holds nothing, rather than falling back to everything', () => {
    expect(inRange(stretches, [31_000, 35_000])).toEqual([]);
  });
});

describe('clamp', () => {
  it('holds a value between the two ends it is given', () => {
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(-5, 0, 10)).toBe(0);
    expect(clamp(50, 0, 10)).toBe(10);
  });
});

describe('the brush in the address bar', () => {
  it('reads a stretch a link named', () => {
    expect(readRange(new URLSearchParams('at=20000&until=30000'))).toEqual([20_000, 30_000]);
  });

  it('reads no stretch when the address names none, so the page opens on the whole run', () => {
    expect(readRange(new URLSearchParams(''))).toBeNull();
  });

  it('refuses a stretch a hand-typed address got wrong, rather than brushing somewhere nobody asked for', () => {
    expect(readRange(new URLSearchParams('at=soon&until=30000'))).toBeNull();
    expect(readRange(new URLSearchParams('at=30000&until=20000'))).toBeNull();
    expect(readRange(new URLSearchParams('at=20000'))).toBeNull();
  });

  it('writes the stretch as whole milliseconds', () => {
    expect(withRange(new URLSearchParams(''), [20_000.4, 30_000.6]).toString()).toBe('at=20000&until=30001');
  });

  it('takes the stretch off the address when the brush is cleared', () => {
    expect(withRange(new URLSearchParams('at=1&until=2&step=7'), null).toString()).toBe('step=7');
  });

  it('keeps the parameters it was given, so brushing never throws a filter away', () => {
    const written = withRange(new URLSearchParams('from=2026-09-14&to=2026-09-14'), [1, 2]);

    expect(written.get('from')).toBe('2026-09-14');
  });
});
