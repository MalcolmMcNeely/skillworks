// PROTOTYPE — throwaway. Where the Prompt goes back on the Session page, in three variants switched by ?variant=.
/* eslint-disable react/refs -- the latch only keeps old content on screen while the drawer slides out */
import { useRef } from 'react';
import type { Band } from '../../lib/timeline/conversation';
import type { Mark } from '../../lib/steps';

export interface Opened {
  band: Band;
  // Null when the reader clicked the Exchange itself, not one Step in it.
  mark: Mark | null;
}

// The last Exchange that started at or before the Step, as a Step belongs to the Prompt that came before it.
export function bandOf(bands: readonly Band[], atMs: number): Band | null {
  let found: Band | null = null;

  for (const band of bands) {
    if (band.startMs <= atMs + 1) {
      found = band;
    }
  }

  return found;
}

export function marksIn(marks: readonly Mark[], bands: readonly Band[], band: Band): Mark[] {
  const next = bands.find((each) => each.exchange.index === band.exchange.index + 1);
  const end = next?.startMs ?? Number.POSITIVE_INFINITY;

  return marks.filter((mark) => mark.startMs >= band.startMs - 1 && mark.startMs < end);
}

export function openedOf(
  bands: readonly Band[],
  marks: readonly Mark[],
  step: string | null,
  exchange: number | null,
): Opened | null {
  if (step !== null) {
    const mark = marks.find((each) => each.step.id === step);
    const band = mark === undefined ? null : bandOf(bands, mark.startMs);

    return mark === undefined || band === null ? null : { band, mark };
  }

  const band = exchange === null ? undefined : bands.find((each) => each.exchange.index === exchange);

  return band === undefined ? null : { band, mark: null };
}

// Keeps the last content while the drawer slides out, so it never empties mid-slide.
export function useLatch<T>(value: T | null): T | null {
  const last = useRef<T | null>(value);

  if (value !== null) {
    last.current = value;
  }

  return last.current;
}

export function describeWithheld(length: number): string {
  return length === 0 ? 'Nothing was recorded.' : `Withheld · ${length.toLocaleString('en-GB')} characters`;
}
