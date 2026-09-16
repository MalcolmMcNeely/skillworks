import { filterParams, type Filter } from '../../filters/lib/filters';
import { getLines } from '../../http/api/json';
import type { ActivationsLine } from '../lib/activations';

export function fetchActivations(filter: Filter, signal: AbortSignal): AsyncGenerator<ActivationsLine> {
  const query = filterParams(filter).toString();

  return getLines<ActivationsLine>(`/api/activations${query === '' ? '' : `?${query}`}`, signal);
}
