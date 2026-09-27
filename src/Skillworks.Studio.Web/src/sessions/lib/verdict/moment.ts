import type { Named } from './findings';
import { showInTimeline } from './showInTimeline';
import type { Mark } from '../steps';
import { inSpell, type Spell } from '../timeline/view';

// A card with more than a handful reads as a list, and the Timeline is where a reader goes for the rest.
export const mostFaults = 5;

export interface Moment {
  // The same span the Timeline moves to, so the card's drawing and the lanes it opens show one moment.
  spell: Spell;
  marks: Mark[];
  faults: Mark[];
}

export function momentOf(named: Named, marks: readonly Mark[], whole: Spell): Moment {
  const spell = showInTimeline(named, whole).view;
  const held = inSpell(marks, spell);

  return {
    spell,
    marks: held,
    faults: held
      .filter((mark) => mark.step.fault)
      .toSorted((one, other) => one.startMs - other.startMs)
      .slice(0, mostFaults),
  };
}
