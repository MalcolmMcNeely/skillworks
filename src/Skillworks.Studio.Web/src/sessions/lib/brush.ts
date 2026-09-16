import type { Range } from './steps';

export function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}

// Either end of a brush may be dragged past the other, so the two moments can arrive the wrong way round.
export function rangeOf(one: number, other: number, whole: Range): Range {
  return [clamp(Math.min(one, other), whole[0], whole[1]), clamp(Math.max(one, other), whole[0], whole[1])];
}

// Padded, so the Step a reader asked for never sits flush against the edge of the lanes.
export function widened(stretch: Range, whole: Range, least = 20_000): Range {
  const pad = Math.max(least, (stretch[1] - stretch[0]) * 0.08);

  return rangeOf(stretch[0] - pad, stretch[1] + pad, whole);
}

// Counts moments or pixels alike, as the brush is dragged in one, read in the other, and moved whole in both.
export function moved(pair: [number, number], by: number, bounds: [number, number]): [number, number] {
  const held = pair[1] - pair[0];
  const start = clamp(pair[0] + by, bounds[0], bounds[1] - held);

  return [start, start + held];
}

// No brush is the whole run, so every panel beneath reads everything until a reader asks for less.
export function holds(range: Range | null, startMs: number, endMs: number): boolean {
  return range === null || (endMs >= range[0] && startMs <= range[1]);
}

const at = 'at';

const until = 'until';

// The brush lives in the address bar, so a stretch of a run can be linked to and reloaded.
export function readRange(params: URLSearchParams): Range | null {
  const from = Number(params.get(at));
  const to = Number(params.get(until));

  if (!params.has(at) || !params.has(until) || !Number.isFinite(from) || !Number.isFinite(to) || to <= from) {
    return null;
  }

  return [from, to];
}

export function withRange(params: URLSearchParams, range: Range | null): URLSearchParams {
  const written = new URLSearchParams(params);

  if (range === null) {
    written.delete(at);
    written.delete(until);
  } else {
    written.set(at, String(Math.round(range[0])));
    written.set(until, String(Math.round(range[1])));
  }

  return written;
}
