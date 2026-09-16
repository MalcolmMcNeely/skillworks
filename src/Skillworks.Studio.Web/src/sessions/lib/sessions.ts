import type { Span } from '../../filters/lib/filters';
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
}

export interface SessionsHead {
  kind: 'head';
  span: Span & { lookback: boolean; fromUtc: string; untilUtc: string };
}

export interface SessionsPage {
  kind: 'sessions';
  sessions: Session[];
}

export type SessionsLine = SessionsHead | SessionsPage | GapEnd;

export interface SessionsAnswer {
  span: SessionsHead['span'];
  sessions: Session[];
  // No rows yet is not the same as no runs, so the table waits for this rather than for the answer to end.
  landed: boolean;
  arriving: boolean;
  // Null while arriving, as whether the answer fell short is known only once it ends.
  gap: Gap | null;
}

export function foldSessionsLine(answer: SessionsAnswer | null, line: SessionsLine): SessionsAnswer {
  if (line.kind === 'head') {
    return { span: line.span, sessions: [], landed: false, arriving: true, gap: null };
  }

  if (answer === null) {
    throw new Error(`A sessions answer starts with its head, not a ${line.kind} line.`);
  }

  if (line.kind === 'end') {
    return { ...answer, arriving: false, gap: line.gap };
  }

  return { ...answer, sessions: line.sessions, landed: true };
}

// A run with no origin remote has no Repository, which is a thing Studio knows rather than one it cannot say.
export const noRepository = 'None';

export const notKnown = 'Not known';

const minute = 60_000;

const hour = 60 * minute;

export function describeLength(lengthMs: number): string {
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

export function describeSpan(span: SessionsHead['span']): string {
  return span.from === span.to ? span.from : `${span.from} to ${span.to}`;
}
