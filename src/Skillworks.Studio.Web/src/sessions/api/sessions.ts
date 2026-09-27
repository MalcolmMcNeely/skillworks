import { everything, filterParams, filterQuery, type Filter, type Span } from '../../shared/filters/lib/filters';
import { getLines } from '../../shared/wire/api/json';
import { listFilter, type SessionsLine } from '../lib/sessions';
import type { SessionLine } from '../lib/steps';

export function fetchSessions(filter: Filter, signal: AbortSignal): AsyncGenerator<SessionsLine> {
  return getLines<SessionsLine>(`/api/sessions${filterQuery(listFilter(filter))}`, signal);
}

// A span and nothing else: the id already names one run, so a Repository or a Skill could only narrow it away.
export function fetchSession(id: string, span: Span, signal: AbortSignal): AsyncGenerator<SessionLine> {
  const query = filterParams({ ...everything, ...span }).toString();

  return getLines<SessionLine>(`/api/sessions/${encodeURIComponent(id)}${query === '' ? '' : `?${query}`}`, signal);
}
