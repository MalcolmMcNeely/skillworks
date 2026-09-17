import { describe, expect, it } from 'vitest';
import { foldScale, foldsOver, ticksOf } from './fold';

const minute = 60_000;

const hour = 60 * minute;

const width = 1_000;

// Two short bursts of work eleven hours apart, which is the run the fold exists for.
const longDay: [number, number][] = [
  [0, 5 * minute],
  [11 * hour, 11 * hour + 5 * minute],
];

describe('foldScale', () => {
  it('joins spells closer together than the threshold into one segment', () => {
    const scale = foldScale(
      [
        [0, minute],
        [2 * minute, 3 * minute],
      ],
      0,
      width,
    );

    expect(scale.segments).toHaveLength(1);
    expect(scale.folds).toHaveLength(0);
  });

  it('folds an idle pause over the threshold, and says how long it was', () => {
    const scale = foldScale(longDay, 0, width);

    expect(scale.segments).toHaveLength(2);
    expect(scale.folds).toHaveLength(1);
    expect(scale.folds[0].toMs - scale.folds[0].fromMs).toBe(11 * hour - 5 * minute);
  });

  it('fits an eleven-hour run on one screen, giving the work almost all of the width', () => {
    const scale = foldScale(longDay, 0, width);
    const working = scale.segments.reduce((sum, [from, to]) => sum + (scale.map(to) - scale.map(from)), 0);

    // Unfolded, ten minutes of work in eleven hours would take under two pixels of a thousand.
    expect(working).toBeGreaterThan(width * 0.75);
    expect(scale.map(longDay[1][1])).toBeLessThanOrEqual(width);
  });

  it('opens at the left edge and closes at the right, so the run fills the strip it is given', () => {
    const scale = foldScale(longDay, 100, 900);

    expect(scale.map(scale.segments[0][0])).toBeCloseTo(100, 6);
    expect(scale.map(scale.segments.at(-1)![1])).toBeCloseTo(900, 6);
  });

  it('reads a pixel back as the moment it was drawn from', () => {
    const scale = foldScale(longDay, 0, width);
    const moment = 11 * hour + 2 * minute;

    expect(scale.invert(scale.map(moment))).toBeCloseTo(moment, 3);
  });

  it('holds a moment inside a fold to the nearer segment of work, so a cursor never reads an idle instant', () => {
    const scale = foldScale(longDay, 0, width);

    expect(scale.invert(scale.map(2 * hour))).toBe(scale.segments[0][1]);
    expect(scale.invert(scale.map(10 * hour))).toBe(scale.segments[1][0]);
  });

  it('takes a threshold of its own, so a shorter idle pause can be folded too', () => {
    const scale = foldScale(
      [
        [0, minute],
        [2 * minute, 3 * minute],
      ],
      0,
      width,
      30_000,
    );

    expect(scale.segments).toHaveLength(2);
  });

  it('draws a run of one instant step on an axis of its own, rather than on none at all', () => {
    const scale = foldScale([[1_000, 1_000]], 0, width);

    expect(scale.segments).toHaveLength(1);
    expect(scale.map(1_000)).toBeCloseTo(0, 6);
    expect(Number.isFinite(scale.map(1_000))).toBe(true);
  });

  it('draws an axis for a run with no steps at all', () => {
    const scale = foldScale([], 0, width);

    expect(scale.segments).toHaveLength(1);
    expect(Number.isFinite(scale.map(0))).toBe(true);
  });

  it('folds over three minutes by default', () => {
    expect(foldsOver).toBe(3 * minute);
  });
});

describe('ticksOf', () => {
  it('puts every tick on a round moment inside a segment that holds work', () => {
    const scale = foldScale(longDay, 0, width);

    for (const tick of ticksOf(scale)) {
      expect(scale.segments.some(([from, to]) => tick.ms >= from && tick.ms <= to)).toBe(true);
    }
  });

  it('keeps the ticks far enough apart to be read', () => {
    const scale = foldScale(longDay, 0, width);
    const ticks = ticksOf(scale, 70);

    expect(ticks.length).toBeGreaterThan(0);

    for (let index = 1; index < ticks.length; index += 1) {
      expect(ticks[index].x - ticks[index - 1].x).toBeGreaterThanOrEqual(70);
    }
  });
});
