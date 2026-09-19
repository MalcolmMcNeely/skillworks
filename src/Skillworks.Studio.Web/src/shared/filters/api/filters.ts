import { getLines } from '../../wire/api/json';
import type { FilterChoicesLine } from '../lib/choices';
import { everything, filterQuery, type Span } from '../lib/filters';

export function fetchFilterChoices(span: Span, signal: AbortSignal): AsyncGenerator<FilterChoicesLine> {
  return getLines<FilterChoicesLine>(`/api/filters${filterQuery({ ...everything, from: span.from, to: span.to })}`, signal);
}
