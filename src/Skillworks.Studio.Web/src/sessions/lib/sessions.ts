import type { SymbolTable } from '../../shared/alphabets/lib/alphabets';
import { filterParams, type Filter } from '../../shared/filters/lib/filters';
import type { Gap, GapEnd } from '../../shared/gaps/lib/gaps';

export type Depth = 'thin' | 'full';

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
  latestUtc: string;
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

export type Landing<T> =
  | { state: 'landed'; value: T }
  | { state: 'arriving' }
  | { state: 'fellShort' };

export type Measured = Landing<number>;

export interface DrawnSession {
  session: SessionRow;
  measures: Record<MeasureName, Measured>;
  depth: Landing<Depth>;
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
  'Depth',
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

export interface SessionsDepths {
  kind: 'depths';
  // A row this does not name has a Depth nobody could read, which is a dash and never Thin.
  depths: Record<string, Depth>;
}

// At most one of the two: a read either stopped at a Latest or ran out of Prompts at the end of its 30 days.
export interface SessionsEnd extends GapEnd {
  // So the next read starts where this one stopped.
  oldestLatestUtc: string | null;
  // How far back a quiet 30 days reached, so a quiet month is never read as the start of the store.
  quietSinceUtc: string | null;
}

export type SessionsLine = SessionsHead | SessionsPage | SessionsMeasure | SessionsDepths | SessionsEnd;

export interface SessionsAnswer {
  asOfUtc: string;
  rows: DrawnSession[];
  // No rows yet is not the same as no runs, so the table waits for this rather than for the answer to end.
  landed: boolean;
  arriving: boolean;
  // Null while arriving, as whether the answer fell short is known only once it ends.
  gap: Gap | null;
  // While a later read is in flight, the Latest it started from, so a read that fails can be asked again.
  oldestLatestUtc: string | null;
  quietSinceUtc: string | null;
  held: number;
}

export interface LaterRead {
  asOfUtc: string;
  latestBeforeUtc: string;
}

export type ReadOnState = 'hidden' | 'ready' | 'arriving';

const arriving = { state: 'arriving' } as const;

const fellShort = { state: 'fellShort' } as const;

const unread: Record<MeasureName, Measured> = {
  toolCalls: arriving,
  cost: arriving,
  faults: arriving,
  friction: arriving,
};

export function foldSessionsLine(answer: SessionsAnswer | null, line: SessionsLine): SessionsAnswer {
  if (line.kind === 'head') {
    return answer === null
      ? {
          asOfUtc: line.asOfUtc,
          rows: [],
          landed: false,
          arriving: true,
          gap: null,
          oldestLatestUtc: null,
          quietSinceUtc: null,
          held: 0,
        }
      : { ...answer, asOfUtc: line.asOfUtc, arriving: true, gap: null, held: answer.rows.length };
  }

  if (answer === null) {
    throw new Error(`A sessions answer starts with its head, not a ${line.kind} line.`);
  }

  if (line.kind === 'sessions') {
    return {
      ...answer,
      rows: [
        ...answer.rows.slice(0, answer.held),
        ...line.sessions.map((session) => ({ session, measures: unread, depth: arriving })),
      ],
      landed: true,
    };
  }

  if (line.kind === 'measure') {
    return { ...answer, rows: inRead(answer, (row) => landedIn(row, line)) };
  }

  if (line.kind === 'depths') {
    return { ...answer, rows: inRead(answer, (row) => ({ ...row, depth: depthIn(row, line) })) };
  }

  // A store that did not answer brought no Latest, so the one the read started from stays for the next click.
  const ended = line.oldestLatestUtc !== null || line.quietSinceUtc !== null || line.gap.kind !== 'unreachable';
  const { oldestLatestUtc, quietSinceUtc } = ended ? line : answer;

  return { ...answer, arriving: false, gap: line.gap, oldestLatestUtc, quietSinceUtc, rows: inRead(answer, settled) };
}

export function failSessionsRead(answer: SessionsAnswer, reason: string): SessionsAnswer {
  return { ...answer, arriving: false, gap: { kind: 'unreachable', missing: reason }, rows: inRead(answer, settled) };
}

// Only a finished read names where the next one starts, so the button waits for it.
export function loadMore(answer: SessionsAnswer): ReadOnState {
  return offered(answer, answer.oldestLatestUtc);
}

export function lookFurtherBack(answer: SessionsAnswer): ReadOnState {
  return offered(answer, answer.quietSinceUtc);
}

export function readOn(answer: SessionsAnswer): ReadOnState {
  return offered(answer, answer.oldestLatestUtc ?? answer.quietSinceUtc);
}

function offered(answer: SessionsAnswer, from: string | null): ReadOnState {
  if (from === null) {
    return 'hidden';
  }

  return answer.arriving ? 'arriving' : 'ready';
}

export function nextRead(answer: SessionsAnswer): LaterRead | null {
  const latestBeforeUtc = answer.oldestLatestUtc ?? answer.quietSinceUtc;

  return latestBeforeUtc === null ? null : { asOfUtc: answer.asOfUtc, latestBeforeUtc };
}

// Said only once the read has ended, as a further read in flight may yet find work past the date.
export function describeQuiet(answer: SessionsAnswer): string | null {
  return answer.arriving || answer.quietSinceUtc === null
    ? null
    : `No older Prompts back to ${answer.quietSinceUtc.slice(0, 10)}.`;
}

// Only a later read's shortfall goes under the rows, as the first read's already stands in the head.
export function laterShortfall(answer: SessionsAnswer): Gap | null {
  return answer.held > 0 && answer.gap !== null && answer.gap.kind === 'unreachable' ? answer.gap : null;
}

function inRead(answer: SessionsAnswer, change: (row: DrawnSession) => DrawnSession): DrawnSession[] {
  return answer.rows.map((row, index) => (index < answer.held ? row : change(row)));
}

function landedIn(row: DrawnSession, line: SessionsMeasure): DrawnSession {
  const value = line.values[row.session.id] ?? 0;

  return { ...row, measures: { ...row.measures, [line.measure]: { state: 'landed', value } } };
}

function depthIn(row: DrawnSession, line: SessionsDepths): Landing<Depth> {
  const value = line.depths[row.session.id];

  return value === undefined ? fellShort : { state: 'landed', value };
}

// Nothing comes after the end line, so a Measure or a Depth still blank is one the store could not read.
function settled(row: DrawnSession): DrawnSession {
  return {
    ...row,
    measures: {
      toolCalls: read(row.measures.toolCalls),
      cost: read(row.measures.cost),
      faults: read(row.measures.faults),
      friction: read(row.measures.friction),
    },
    depth: read(row.depth),
  };
}

function read<T>(landing: Landing<T>): Landing<T> {
  return landing.state === 'arriving' ? fellShort : landing;
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

const day = 24 * hour;

const reach = 30;

// Counted from the answer's own instants, so the page never knows how far a read is set to look.
export function daysLookedBack(answer: SessionsAnswer): number | null {
  return answer.quietSinceUtc === null
    ? null
    : Math.round((Date.parse(answer.asOfUtc) - Date.parse(answer.quietSinceUtc)) / day);
}

// Each Look further back reaches another 30 days, so an empty list with nothing narrowed says how far it has looked.
export function describeNoSessions(filter: Filter, answer: SessionsAnswer): string {
  if (filter.repository !== '' || filter.skill !== '') {
    return 'No runs match this filter.';
  }

  return `No runs in the last ${daysLookedBack(answer) ?? reach} days.`;
}
