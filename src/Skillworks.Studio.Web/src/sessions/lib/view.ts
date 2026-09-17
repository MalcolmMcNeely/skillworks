export type Range = [number, number];

export function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}

// Either end of a View may be dragged past the other, so the two moments can arrive the wrong way round.
export function rangeOf(one: number, other: number, whole: Range): Range {
  return [clamp(Math.min(one, other), whole[0], whole[1]), clamp(Math.max(one, other), whole[0], whole[1])];
}

// The Step a reader asked for never sits flush against the edge of the lanes.
export function widened(view: Range, whole: Range, least = 20_000): Range {
  const pad = Math.max(least, (view[1] - view[0]) * 0.08);

  return rangeOf(view[0] - pad, view[1] + pad, whole);
}

// Counts moments or pixels alike, as a View is dragged in one, read in the other, and moved whole in both.
export function moved(pair: [number, number], by: number, bounds: [number, number]): [number, number] {
  const held = pair[1] - pair[0];
  const start = clamp(pair[0] + by, bounds[0], bounds[1] - held);

  return [start, start + held];
}

// No View is the whole run, so every panel beneath reads everything until a reader asks for less.
export function holds(view: Range | null, startMs: number, endMs: number): boolean {
  return view === null || (endMs >= view[0] && startMs <= view[1]);
}

// A Step's mark and an Exchange's band alike, so every panel beneath the View narrows the same way.
export function inRange<T extends { startMs: number; endMs: number }>(items: readonly T[], view: Range | null): T[] {
  return items.filter((item) => holds(view, item.startMs, item.endMs));
}

// A Skill fires at an instant, so a View holds the Activations made in it and not the ones still working through it.
export function madeIn<T extends { atMs: number }>(instants: readonly T[], view: Range | null): T[] {
  return instants.filter((instant) => view === null || (instant.atMs >= view[0] && instant.atMs < view[1]));
}

const at = 'at';

const until = 'until';

// A View lives in the address bar, so a part of a run can be linked to and reloaded.
export function readRange(params: URLSearchParams): Range | null {
  const from = Number(params.get(at));
  const to = Number(params.get(until));

  if (!params.has(at) || !params.has(until) || !Number.isFinite(from) || !Number.isFinite(to) || to <= from) {
    return null;
  }

  return [from, to];
}

export function withRange(params: URLSearchParams, view: Range | null): URLSearchParams {
  const written = new URLSearchParams(params);

  if (view === null) {
    written.delete(at);
    written.delete(until);
  } else {
    written.set(at, String(Math.round(view[0])));
    written.set(until, String(Math.round(view[1])));
  }

  return written;
}
