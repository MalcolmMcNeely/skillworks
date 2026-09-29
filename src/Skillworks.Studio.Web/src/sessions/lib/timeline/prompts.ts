import { describeCount } from '../../../shared/figures/lib/figures';
import { readWhere, withWhere, type Where } from '../../../shared/session/lib/where';
import type { Mark } from '../steps';
import type { Band } from './conversation';

// A Step answers the last Prompt typed before it, so one after the last Exchange ended still belongs to it.
export function exchangeOf(mark: Mark, bands: readonly Band[]): Band | null {
  let found: Band | null = null;

  for (const band of bands) {
    if (band.startMs <= mark.startMs) {
      found = band;
    }
  }

  return found;
}

export interface PromptRow {
  band: Band | null;
  open: boolean;
}

export type Opened = Pick<Where, 'step' | 'exchange'>;

export function promptsOf(marks: readonly Mark[], bands: readonly Band[], opened: Opened): PromptRow[] {
  const open = openOf(marks, bands, opened);
  const rows = bands.map((band) => ({ band, open: open === band }));

  return marks.some((mark) => exchangeOf(mark, bands) === null) ? [{ band: null, open: open === null }, ...rows] : rows;
}

export function describeUnsaid(words: string | null, length: number): string | null {
  if (words !== null && words !== '') {
    return null;
  }

  return length === 0 ? 'Nothing was recorded' : `Withheld · ${describeCount(length)} characters`;
}

// One write for all three, as any one left behind opens the drawer again on a reload.
export function closedPrompts(params: URLSearchParams): URLSearchParams {
  return withWhere(params, { ...readWhere(params), step: null, exchange: null, prompts: false });
}

// Undefined where no row is open, as null is the row for the Steps from before the first Prompt.
function openOf(marks: readonly Mark[], bands: readonly Band[], opened: Opened): Band | null | undefined {
  if (opened.step !== null) {
    const mark = marks.find((each) => each.step.id === opened.step);

    return mark === undefined ? undefined : exchangeOf(mark, bands);
  }

  return bands.find((band) => band.exchange.index === opened.exchange);
}
