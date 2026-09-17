import type { SymbolTable } from '../../alphabets/lib/alphabets';
import { narrowsByDepth } from '../../filters/lib/depthKeys';
import type { Filter, Span } from '../../filters/lib/filters';
import type { Gap, GapEnd } from '../../gaps/lib/gaps';

export interface Session {
  id: string;
  startedUtc: string;
  // Null where no event named one, which an older Claude Code and a checkout with no remote both do.
  repository: string | null;
  person: string | null;
  name: string;
  lengthMs: number;
  running: boolean;
  toolCalls: number;
  cost: number;
  faults: number;
  // Never added to Faults: somebody chose a refusal and a hook block, so a clean run still reads clean.
  friction: number;
}

export type SessionSort = 'started' | 'repository' | 'person' | 'name' | 'length' | 'toolCalls' | 'cost' | 'faults';

export interface SessionColumn {
  sort: SessionSort;
  heading: string;
}

export const sessionColumns: readonly SessionColumn[] = [
  { sort: 'started', heading: 'Started' },
  { sort: 'repository', heading: 'Repository' },
  { sort: 'person', heading: 'Person' },
  { sort: 'name', heading: 'Session' },
  { sort: 'length', heading: 'Length' },
  { sort: 'toolCalls', heading: 'Tool calls' },
  { sort: 'cost', heading: 'Cost' },
  { sort: 'faults', heading: 'Faults' },
];

export const sortGlyphs = { ascending: '▲', descending: '▼' } as const;

// Which way a column runs is a job of its own, so its two marks are an alphabet of their own.
export const sortSymbols: SymbolTable = { alphabet: 'order', glyphs: Object.values(sortGlyphs) };

export interface SessionsHead {
  kind: 'head';
  span: Span & { lookback: boolean; fromUtc: string; untilUtc: string };
  sort: SessionSort;
  descending: boolean;
}

export interface SessionsPage {
  kind: 'sessions';
  sessions: Session[];
}

export type SessionsLine = SessionsHead | SessionsPage | GapEnd;

export interface SessionsAnswer {
  span: SessionsHead['span'];
  // The order the answer was read in, which is the only order a heading may mark.
  sort: SessionSort;
  descending: boolean;
  sessions: Session[];
  // No rows yet is not the same as no runs, so the table waits for this rather than for the answer to end.
  landed: boolean;
  arriving: boolean;
  // Null while arriving, as whether the answer fell short is known only once it ends.
  gap: Gap | null;
}

export function foldSessionsLine(answer: SessionsAnswer | null, line: SessionsLine): SessionsAnswer {
  if (line.kind === 'head') {
    return {
      span: line.span,
      sort: line.sort,
      descending: line.descending,
      sessions: [],
      landed: false,
      arriving: true,
      gap: null,
    };
  }

  if (answer === null) {
    throw new Error(`A sessions answer starts with its head, not a ${line.kind} line.`);
  }

  if (line.kind === 'end') {
    return { ...answer, arriving: false, gap: line.gap };
  }

  return { ...answer, sessions: line.sessions, landed: true };
}

export interface SessionOrder {
  sort: SessionSort;
  // Null leaves the direction to the answer, which opens a column the way a reader wants it first.
  descending: boolean | null;
}

export type SortedBy = Pick<SessionsAnswer, 'sort' | 'descending'>;

export const opensOn: SessionOrder = { sort: 'started', descending: null };

export function nextOrder(shown: SortedBy | null, sort: SessionSort): SessionOrder {
  return shown !== null && shown.sort === sort ? { sort, descending: !shown.descending } : { sort, descending: null };
}

// The address bar can name a column the table lacks, and the answer would sort on another without saying so.
export function readOrder(params: URLSearchParams): SessionOrder {
  const asked = params.get('sort');
  const known = sessionColumns.find((column) => column.sort === asked);
  const descending = params.get('descending');

  return {
    sort: known?.sort ?? opensOn.sort,
    descending: descending === null ? null : descending === 'true',
  };
}

// The address bar and the API take the same parameters, and the opening order is left out, so an
// untouched table has a clean address to share.
export function withOrder(params: URLSearchParams, order: SessionOrder): URLSearchParams {
  const written = new URLSearchParams(params);

  if (order.sort === opensOn.sort && order.descending === null) {
    written.delete('sort');
  } else {
    written.set('sort', order.sort);
  }

  if (order.descending === null) {
    written.delete('descending');
  } else {
    written.set('descending', String(order.descending));
  }

  return written;
}

// A run with no origin remote has no Repository, which is a thing Studio knows rather than one it cannot say.
export const noRepository = 'None';

export const notKnown = 'Not known';

const minute = 60_000;

const hour = 60 * minute;

export function describeRunLength(lengthMs: number): string {
  const hours = Math.floor(lengthMs / hour);
  const minutes = Math.round((lengthMs - hours * hour) / minute);

  // Under a minute is still a run, so it reads as under a minute rather than as nothing at all.
  if (hours === 0 && minutes === 0) {
    return '< 1m';
  }

  return hours === 0 ? `${minutes}m` : `${hours}h ${minutes}m`;
}

// UTC, as the Filter counts whole UTC days, so a row's time and its day always agree.
export function describeStarted(startedUtc: string): string {
  return startedUtc.replace('T', ' ').slice(0, 16);
}

export function describeSpan(span: Span): string {
  return span.from === span.to ? span.from : `${span.from} to ${span.to}`;
}

// The API decides the lookback's length, so before an answer lands only a span a reader asked for is known.
export function describePeriod(span: SessionsHead['span'] | null, shown: Span | null): string {
  if (span !== null) {
    return `${span.lookback ? 'The lookback, ' : ''}${describeSpan(span)}`;
  }

  return shown === null ? 'The lookback' : describeSpan(shown);
}

// A span is the period itself, so only the other three parts turn an empty table from a quiet week into no match.
export function describeNoSessions(filter: Filter): string {
  const narrowed = filter.repository !== '' || filter.skill !== '' || narrowsByDepth(filter);

  return narrowed ? 'No runs match this filter.' : 'No runs in this period.';
}
