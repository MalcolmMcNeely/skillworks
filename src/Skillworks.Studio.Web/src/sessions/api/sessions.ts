import { everything, filterParams, filterQuery, type Filter, type Span } from '../../shared/filters/lib/filters';
import { getLines } from '../../shared/wire/api/json';
import { listFilter, type LaterRead, type SessionsLine } from '../lib/sessions';
import type { SessionLine } from '../lib/steps';

export function fetchSessions(
  filter: Filter,
  signal: AbortSignal,
  later: LaterRead | null = null,
): AsyncGenerator<SessionsLine> {
  if (later === null) {
    return getLines<SessionsLine>(`/api/sessions${filterQuery(listFilter(filter))}`, signal);
  }

  const params = filterParams(listFilter(filter));

  params.set('asOf', later.asOfUtc);
  params.set('latestBefore', later.latestBeforeUtc);

  return getLines<SessionsLine>(`/api/sessions?${params.toString()}`, signal);
}

// The id and nothing else: a Lookup names one run, so the Filter and the paging have nothing to narrow.
export function fetchLookup(id: string, signal: AbortSignal): AsyncGenerator<SessionsLine> {
  return getLines<SessionsLine>(`/api/sessions?lookup=${encodeURIComponent(id)}`, signal);
}

// A span and nothing else: the id already names one run, so a Repository or a Skill could only narrow it away.
export function fetchSession(id: string, span: Span, signal: AbortSignal): AsyncGenerator<SessionLine> {
  const query = filterParams({ ...everything, ...span }).toString();

  return getLines<SessionLine>(`/api/sessions/${encodeURIComponent(id)}${query === '' ? '' : `?${query}`}`, signal);
}
