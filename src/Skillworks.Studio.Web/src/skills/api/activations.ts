import { filterParams, type Filter } from '../../shared/filters/lib/filters';
import { getLines } from '../../shared/http/api/json';
import type { ActivationsLine } from '../lib/activations';

export function fetchActivations(filter: Filter, signal: AbortSignal): AsyncGenerator<ActivationsLine> {
  const query = filterParams(filter).toString();

  return getLines<ActivationsLine>(`/api/activations${query === '' ? '' : `?${query}`}`, signal);
}
