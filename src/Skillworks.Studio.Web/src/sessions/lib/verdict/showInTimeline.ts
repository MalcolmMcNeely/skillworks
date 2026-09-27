import type { Named } from './findings';
import { widened, type Spell } from '../timeline/view';

export interface Shown {
  view: Spell;
  // Null for a Finding about a length of time, so a Step the reader left open closes rather than sitting beside it.
  step: string | null;
}

export function showInTimeline(named: Named, whole: Spell): Shown {
  return { view: widened([named.startMs, named.endMs], whole), step: named.finding.step };
}
