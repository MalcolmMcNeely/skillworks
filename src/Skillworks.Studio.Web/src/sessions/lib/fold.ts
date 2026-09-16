export interface Fold {
  x: number;
  fromMs: number;
  toMs: number;
}

export interface FoldScale {
  map: (ms: number) => number;
  invert: (x: number) => number;
  segments: readonly (readonly [number, number])[];
  folds: readonly Fold[];
  msPerPx: number;
}

// Long enough that a pause for thought stays on the axis, short enough that a walk away from the keyboard folds.
export const foldsOver = 3 * 60_000;

// The width a fold takes, so a reader sees the run stop and start again rather than one unbroken stretch.
const foldPx = 22;

// Never more than this share of the width, or a run of many folds would be all folds.
const foldShare = 0.2;

// Without it an instant Step is a segment of no width at all, and nothing inside it can be mapped.
const leastMs = 500;

// Without the fold, an eleven-hour run is a thin smear of work between long empty stretches.
export function foldScale(
  spells: readonly (readonly [number, number])[],
  x0: number,
  x1: number,
  foldMs = foldsOver,
): FoldScale {
  const segments = joined(spells, foldMs);
  const gaps = segments.length - 1;
  const gapPx = gaps > 0 ? Math.min(foldPx, ((x1 - x0) * foldShare) / gaps) : 0;
  const held = segments.reduce((sum, [from, to]) => sum + (to - from), 0);
  const width = Math.max(1, x1 - x0 - gapPx * gaps);
  const pixels: [number, number][] = [];
  let edge = x0;

  for (const [from, to] of segments) {
    const across = ((to - from) / held) * width;

    pixels.push([edge, edge + across]);
    edge += across + gapPx;
  }

  const map = (ms: number) => {
    const index = holding(segments, ms);

    if (index < 0) {
      return x0;
    }

    const [from, to] = segments[index];

    if (ms <= to) {
      return pixels[index][0] + ((ms - from) / (to - from)) * (pixels[index][1] - pixels[index][0]);
    }

    // Inside a fold, so the reader's cursor still moves forward over a stretch that took no width.
    return index + 1 < segments.length
      ? pixels[index][1] + ((ms - to) / (segments[index + 1][0] - to)) * gapPx
      : pixels[index][1];
  };

  const invert = (x: number) => {
    for (let index = 0; index < pixels.length; index += 1) {
      const [left, right] = pixels[index];

      if (x <= right) {
        const [from, to] = segments[index];

        return from + ((Math.max(left, x) - left) / Math.max(1, right - left)) * (to - from);
      }

      const next = pixels[index + 1];

      // Nothing ran inside a fold, so a cursor there lands on the nearer edge of the work on either side.
      if (next !== undefined && x < next[0]) {
        return x - right <= next[0] - x ? segments[index][1] : segments[index + 1][0];
      }
    }

    return segments[segments.length - 1][1];
  };

  return {
    map,
    invert,
    segments,
    folds: segments.slice(1).map((segment, index) => ({
      x: pixels[index][1] + gapPx / 2,
      fromMs: segments[index][1],
      toMs: segment[0],
    })),
    msPerPx: held / width,
  };
}

function joined(spells: readonly (readonly [number, number])[], foldMs: number): [number, number][] {
  const sorted = spells
    .filter(([from, to]) => Number.isFinite(from) && Number.isFinite(to))
    .map(([from, to]): [number, number] => [from, Math.max(from, to)])
    .toSorted((one, other) => one[0] - other[0]);

  const segments: [number, number][] = [];

  for (const [from, to] of sorted) {
    const last = segments.at(-1);

    if (last !== undefined && from - last[1] <= foldMs) {
      last[1] = Math.max(last[1], to);
    } else {
      segments.push([from, to]);
    }
  }

  // A run of one instant Step still needs an axis to sit on.
  return segments.length === 0 ? [[0, leastMs]] : segments.map(([from, to]) => [from, Math.max(to, from + leastMs)]);
}

function holding(segments: readonly (readonly [number, number])[], ms: number): number {
  let low = 0;
  let high = segments.length - 1;
  let found = -1;

  while (low <= high) {
    const middle = (low + high) >> 1;

    if (segments[middle][0] <= ms) {
      found = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }

  return found;
}

const steps = [1_000, 5_000, 10_000, 30_000, 60_000, 300_000, 600_000, 1_800_000, 3_600_000, 7_200_000, 21_600_000];

// A tick inside a fold would name a moment nothing ran at, so each stretch of work is walked on its own.
export function ticksOf(scale: FoldScale, leastApartPx = 70): { x: number; ms: number }[] {
  const step = steps.find((each) => each / scale.msPerPx >= leastApartPx) ?? steps[steps.length - 1];
  const ticks: { x: number; ms: number }[] = [];
  let lastX = -Infinity;

  for (const [from, to] of scale.segments) {
    for (let ms = Math.ceil(from / step) * step; ms <= to; ms += step) {
      const x = scale.map(ms);

      if (x - lastX >= leastApartPx) {
        ticks.push({ x, ms });
        lastX = x;
      }
    }
  }

  return ticks;
}
