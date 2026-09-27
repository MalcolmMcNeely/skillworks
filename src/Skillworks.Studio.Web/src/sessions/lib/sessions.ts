import type { SymbolTable } from '../../shared/alphabets/lib/alphabets';
import { narrowsByDepth } from '../../shared/filters/lib/depthKeys';
import { filterParams, type Filter } from '../../shared/filters/lib/filters';
import type { Gap, GapEnd } from '../../shared/gaps/lib/gaps';

interface SessionOutline {
  id: string;
  startedUtc: string;
  // Null where no event named one, which an older Claude Code and a checkout with no remote both do.
  repository: string | null;
  person: string | null;
  name: string;
  lengthMs: number;
  running: boolean;
}

// It carries no Measure, so a number still being read costs a reader no rows.
export interface SessionRow extends SessionOutline {
  // The newest Prompt of the whole piece of work, which is the row's place in the list.
  lastActivityUtc: string;
  // Both ends in, from the start to the last event of any Child.
  firstDay: string;
  lastDay: string;
}

// One run's own page counts its Measures from its events, so they ride the head that opens it.
export interface Session extends SessionOutline {
  toolCalls: number;
  cost: number;
  faults: number;
  // Somebody chose it, so it is never added to Faults and a clean run still reads clean.
  friction: number;
}

export type MeasureName = 'toolCalls' | 'cost' | 'faults' | 'friction';

export type Measured =
  | { state: 'landed'; value: number }
  | { state: 'arriving' }
  | { state: 'fellShort' };

export interface DrawnSession {
  session: SessionRow;
  measures: Record<MeasureName, Measured>;
}

export const measureWords = {
  // Never a zero, so a Measure nobody could read never reads as a run that did nothing.
  fellShort: '—',
} as const;

// The dash is drawn, so it answers to the alphabets as any other mark on screen does.
export const measureSymbols: SymbolTable = { alphabet: 'condition', glyphs: [measureWords.fellShort] };

// Plain labels: fifty rows sorted by a column would read as the top of a whole week, and they are not.
export const sessionHeadings: readonly string[] = [
  'Started',
  'Repository',
  'Person',
  'Session',
  'Length',
  'Tool calls',
  'Cost',
  'Faults',
];

export interface SessionsHead {
  kind: 'head';
  // Nothing after it is read, so a later read that passes it back never moves a row already drawn.
  asOfUtc: string;
}

export interface SessionsPage {
  kind: 'sessions';
  sessions: SessionRow[];
}

export interface SessionsMeasure {
  kind: 'measure';
  measure: MeasureName;
  // A run this does not name made none of it, which is a zero rather than a hole.
  values: Record<string, number>;
}

export interface SessionsEnd extends GapEnd {
  // The place of the oldest row read, so the next read starts where this one stopped.
  nextBeforeUtc: string | null;
}

export type SessionsLine = SessionsHead | SessionsPage | SessionsMeasure | SessionsEnd;

export interface SessionsAnswer {
  asOfUtc: string;
  rows: DrawnSession[];
  // No rows yet is not the same as no runs, so the table waits for this rather than for the answer to end.
  landed: boolean;
  arriving: boolean;
  // Null while arriving, as whether the answer fell short is known only once it ends.
  gap: Gap | null;
  nextBeforeUtc: string | null;
}

const arriving: Measured = { state: 'arriving' };

const fellShort: Measured = { state: 'fellShort' };

const unread: Record<MeasureName, Measured> = {
  toolCalls: arriving,
  cost: arriving,
  faults: arriving,
  friction: arriving,
};

export function foldSessionsLine(answer: SessionsAnswer | null, line: SessionsLine): SessionsAnswer {
  if (line.kind === 'head') {
    return {
      asOfUtc: line.asOfUtc,
      rows: [],
      landed: false,
      arriving: true,
      gap: null,
      nextBeforeUtc: null,
    };
  }

  if (answer === null) {
    throw new Error(`A sessions answer starts with its head, not a ${line.kind} line.`);
  }

  if (line.kind === 'sessions') {
    return { ...answer, rows: line.sessions.map((session) => ({ session, measures: unread })), landed: true };
  }

  if (line.kind === 'measure') {
    return { ...answer, rows: answer.rows.map((row) => landedIn(row, line)) };
  }

  return {
    ...answer,
    arriving: false,
    gap: line.gap,
    nextBeforeUtc: line.nextBeforeUtc,
    rows: answer.rows.map(settled),
  };
}

function landedIn(row: DrawnSession, line: SessionsMeasure): DrawnSession {
  const value = line.values[row.session.id] ?? 0;

  return { ...row, measures: { ...row.measures, [line.measure]: { state: 'landed', value } } };
}

// Nothing comes after the end line, so a Measure still blank is one the store could not read.
function settled(row: DrawnSession): DrawnSession {
  return {
    ...row,
    measures: {
      toolCalls: read(row.measures.toolCalls),
      cost: read(row.measures.cost),
      faults: read(row.measures.faults),
      friction: read(row.measures.friction),
    },
  };
}

function read(measured: Measured): Measured {
  return measured.state === 'arriving' ? fellShort : measured;
}

// No span narrows the list, so a span an old link still carries is left off the question.
export function listFilter(filter: Filter): Filter {
  return { ...filter, from: '', to: '' };
}

// The row's own days open the whole run, and the rest of the Filter brings going up back to the same list.
export function rowParams(session: SessionRow, filter: Filter): URLSearchParams {
  return filterParams({ ...filter, from: session.firstDay, to: session.lastDay });
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

// One read looks 30 days back, so an empty list with nothing narrowed says that much and no more.
export function describeNoSessions(filter: Filter): string {
  const narrowed = filter.repository !== '' || filter.skill !== '' || narrowsByDepth(filter);

  return narrowed ? 'No runs match this filter.' : 'No runs in the last 30 days.';
}
