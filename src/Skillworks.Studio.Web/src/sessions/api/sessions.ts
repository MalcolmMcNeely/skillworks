import { filterParams, type Filter } from '../../filters/lib/filters';
import { getLines } from '../../http/api/json';
import { withOrder, type SessionOrder, type SessionsLine } from '../lib/sessions';

export function fetchSessions(filter: Filter, order: SessionOrder, signal: AbortSignal): AsyncGenerator<SessionsLine> {
  const query = withOrder(filterParams(filter), order).toString();

  return getLines<SessionsLine>(`/api/sessions${query === '' ? '' : `?${query}`}`, signal);
}
