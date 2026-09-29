import type { Mark } from '../steps';
import { inSpell, type Spell } from './view';

export interface CostTurn {
  mark: Mark;
  // Counted from nought at the start of the View, as every panel beneath the timeline reads the View alone.
  soFar: number;
}

// In the order they ended, as Claude Code writes a Turn's Cost only once the Turn is over.
export function turnsOf(marks: readonly Mark[], view: Spell | null): CostTurn[] {
  return inSpell(marks, view)
    .filter((mark) => mark.step.kind === 'turn')
    .toSorted((one, other) => one.endMs - other.endMs)
    .reduce<CostTurn[]>((counted, mark) => [...counted, { mark, soFar: (counted.at(-1)?.soFar ?? 0) + mark.step.cost }], []);
}

// About four round ticks a twentieth past the total, so the line never touches the top and every label reads as money.
export function moneyTicksOf(total: number): number[] {
  const wanted = Math.max(total, 0.01) * 1.05;
  const rough = wanted / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const gap = [1, 2, 2.5, 5, 10].map((each) => each * magnitude).find((each) => each >= rough) ?? 10 * magnitude;

  return Array.from({ length: Math.ceil(wanted / gap) + 1 }, (_, index) => index * gap);
}
