export interface Clock {
  now(): number;
  tick(everyMs: number, onTick: () => void): () => void;
}

// The one read of the browser clock in the front end, so a reader looking for it has one file to open.
const browserClock: Clock = {
  now: () => Date.now(),
  tick: (everyMs, onTick) => {
    const ticking = setInterval(onTick, everyMs);

    return () => clearInterval(ticking);
  },
};

// No seam to hand a test its own: a test holds this one still with vi.useFakeTimers, which stops
// the two reads below at their source, so a second way to stand time up would only be the weaker one.
export function clock(): Clock {
  return browserClock;
}
