import { filterQuery, type Filter } from '../../filters/lib/filters';
import { getLines } from '../../http/api/json';
import type { SessionsLine } from '../lib/sessions';

export function fetchSessions(filter: Filter, signal: AbortSignal): AsyncGenerator<SessionsLine> {
  return getLines<SessionsLine>(`/api/sessions${filterQuery(filter)}`, signal);
}
