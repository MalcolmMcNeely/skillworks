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

let held: Clock = browserClock;

export function clock(): Clock {
  return held;
}

export function setClock(still: Clock): void {
  held = still;
}

export function resetClock(): void {
  held = browserClock;
}
