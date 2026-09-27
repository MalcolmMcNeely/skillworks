import type { Named } from './findings';
import type { Mark } from './steps';
import { inRange, widened, type Range } from './view';

// A card with more than a handful reads as a list, and the Timeline is where a reader goes for the rest.
export const mostFaults = 5;

export interface Moment {
  // The same span the Timeline moves to, so the card's drawing and the lanes it opens show one moment.
  extent: Range;
  marks: Mark[];
  faults: Mark[];
}

export function momentOf(named: Named, marks: readonly Mark[], whole: Range): Moment {
  const extent = widened([named.startMs, named.endMs], whole);
  const held = inRange(marks, extent);

  return {
    extent,
    marks: held,
    faults: held
      .filter((mark) => mark.step.fault)
      .toSorted((one, other) => one.startMs - other.startMs)
      .slice(0, mostFaults),
  };
}
