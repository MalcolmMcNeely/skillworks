import { describe, expect, it } from 'vitest';
import { everything } from '../../shared/filters/lib/filters';
import {
  describeNoSessions,
  describePeriod,
  describeRunLength,
  describeSpan,
  describeStarted,
  foldSessionsLine,
  measureSymbols,
  measureWords,
  nextOrder,
  noRepository,
  notKnown,
  opensOn,
  readOrder,
  sessionColumns,
  sortGlyphs,
  sortSymbols,
  takesOrder,
  withOrder,
  type MeasureName,
  type SessionRow,
  type SessionsAnswer,
  type SessionsHead,
} from './sessions';

const head: SessionsHead = {
  kind: 'head',
  span: { from: '2026-09-09', to: '2026-09-15', lookback: true, fromUtc: '2026-09-09T00:00:00+00:00', untilUtc: '2026-09-16T00:00:00+00:00' },
  sort: 'started',
  descending: true,
};

const run: SessionRow = {
  id: '8f1c0a9e-0000-4000-8000-000000000001',
  startedUtc: '2026-09-14T09:00:00+00:00',
  repository: 'malcolmania/skillworks',
  person: 'ada@acme.test',
  name: 'Fixing the failing build',
  lengthMs: 2_460_000,
  running: false,
};

const other: SessionRow = { ...run, id: '8f1c0a9e-0000-4000-8000-000000000002', name: 'Reading the logs' };

const complete = { kind: 'complete', missing: null } as const;

function withRows(...sessions: SessionRow[]): SessionsAnswer {
  return foldSessionsLine(foldSessionsLine(null, head), { kind: 'sessions', sessions });
}

function cell(answer: SessionsAnswer, measure: MeasureName, id: string = run.id) {
  return answer.rows.find((row) => row.session.id === id)?.measures[measure];
}

function withMeasures(answer: SessionsAnswer, ...measures: MeasureName[]): SessionsAnswer {
  return measures.reduce(
    (folded, measure) => foldSessionsLine(folded, { kind: 'measure', measure, values: {} }),
    answer,
  );
}

function orderedColumns(answer: SessionsAnswer) {
  return sessionColumns.filter((column) => takesOrder(answer, column)).map((column) => column.sort);
}

describe('foldSessionsLine', () => {
  it('opens on the span and no rows, so the page says which days it covers before they land', () => {
    const answer = foldSessionsLine(null, head);

    expect(answer).toEqual({
      span: head.span,
      sort: 'started',
      descending: true,
      rows: [],
      landed: false,
      arriving: true,
      gap: null,
    });
  });

  it('takes the order from the head, so a heading marks the column the answer was sorted on', () => {
    const answer = foldSessionsLine(null, { ...head, sort: 'cost', descending: false });

    expect([answer.sort, answer.descending]).toEqual(['cost', false]);
  });

  it('takes the rows from the sessions line and marks them landed, so the table draws before the answer ends', () => {
    const answer = withRows(run);

    expect(answer.rows.map((row) => row.session)).toEqual([run]);
    expect(answer.landed).toBe(true);
    expect(answer.arriving).toBe(true);
  });

  it('marks an answer with no runs landed too, so an empty week is told apart from rows still to come', () => {
    const answer = withRows();

    expect(answer.landed).toBe(true);
    expect(answer.rows).toEqual([]);
  });

  it('ends the answer and keeps its gap, so a screen knows the rows are all there are', () => {
    const answer = foldSessionsLine(withRows(run), { kind: 'end', gap: complete });

    expect(answer.arriving).toBe(false);
    expect(answer.gap).toEqual(complete);
    expect(answer.rows.map((row) => row.session)).toEqual([run]);
  });

  it('stays arriving through its rows and its Measures, so it is complete only once the end line lands', () => {
    const opened = foldSessionsLine(null, head);
    const drawn = foldSessionsLine(opened, { kind: 'sessions', sessions: [run] });
    const measured = withMeasures(drawn, 'cost');

    expect([opened.arriving, drawn.arriving, measured.arriving]).toEqual([true, true, true]);
    expect(foldSessionsLine(measured, { kind: 'end', gap: complete }).arriving).toBe(false);
  });

  it('refuses a line before the head, as a row with no span says nothing about the period', () => {
    expect(() => foldSessionsLine(null, { kind: 'sessions', sessions: [run] })).toThrow(
      'A sessions answer starts with its head, not a sessions line.',
    );
  });
});

describe('the Measures on a folded answer', () => {
  it('leaves every Measure of a fresh row still arriving, so a cell nobody has read yet is blank', () => {
    const answer = withRows(run);

    expect(cell(answer, 'toolCalls')).toEqual({ state: 'arriving' });
    expect(cell(answer, 'cost')).toEqual({ state: 'arriving' });
    expect(cell(answer, 'faults')).toEqual({ state: 'arriving' });
    expect(cell(answer, 'friction')).toEqual({ state: 'arriving' });
  });

  it('fills one column from one Measure line and leaves the rest arriving', () => {
    const answer = foldSessionsLine(withRows(run), {
      kind: 'measure',
      measure: 'cost',
      values: { [run.id]: 1.25 },
    });

    expect(cell(answer, 'cost')).toEqual({ state: 'landed', value: 1.25 });
    expect(cell(answer, 'toolCalls')).toEqual({ state: 'arriving' });
  });

  it('reads a run the Measure does not name as a zero, as a run that made none is named nowhere', () => {
    const answer = foldSessionsLine(withRows(run, other), {
      kind: 'measure',
      measure: 'faults',
      values: { [run.id]: 3 },
    });

    expect(cell(answer, 'faults', other.id)).toEqual({ state: 'landed', value: 0 });
  });

  it('calls a Measure that never came short once the answer ends, so its cells read a dash', () => {
    const landed = foldSessionsLine(withRows(run), {
      kind: 'measure',
      measure: 'cost',
      values: { [run.id]: 1.25 },
    });
    const answer = foldSessionsLine(landed, { kind: 'end', gap: { kind: 'unreachable', missing: 'Tool calls' } });

    expect(cell(answer, 'toolCalls')).toEqual({ state: 'fellShort' });
    expect(cell(answer, 'cost')).toEqual({ state: 'landed', value: 1.25 });
  });

  it('tells a Measure that read as nought from one the Gap names, so a dash is never a zero', () => {
    const nought = foldSessionsLine(withRows(run), { kind: 'measure', measure: 'cost', values: {} });
    const answer = foldSessionsLine(nought, { kind: 'end', gap: { kind: 'unreachable', missing: 'Tool calls' } });

    expect(cell(answer, 'cost')).toEqual({ state: 'landed', value: 0 });
    expect(cell(answer, 'toolCalls')).toEqual({ state: 'fellShort' });
  });
});

describe('takesOrder', () => {
  it('takes no order while the answer is arriving, so no heading asks for one Studio cannot yet give', () => {
    expect(orderedColumns(withRows(run))).toEqual([]);
    expect(orderedColumns(withMeasures(withRows(run), 'toolCalls', 'cost', 'faults'))).toEqual([]);
  });

  it('takes every order once the answer is complete, so the reader can reorder the table', () => {
    const measured = withMeasures(withRows(run), 'toolCalls', 'cost', 'faults', 'friction');
    const answer = foldSessionsLine(measured, { kind: 'end', gap: complete });

    expect(orderedColumns(answer)).toEqual(sessionColumns.map((column) => column.sort));
  });

  it('takes no order on the one Measure that fell short and every order on the rest', () => {
    const measured = withMeasures(withRows(run), 'cost', 'faults', 'friction');
    const answer = foldSessionsLine(measured, { kind: 'end', gap: { kind: 'unreachable', missing: 'Tool calls' } });

    expect(orderedColumns(answer)).toEqual(['started', 'repository', 'person', 'name', 'length', 'cost', 'faults']);
  });
});

describe('describeRunLength', () => {
  it('counts a short run in minutes', () => {
    expect(describeRunLength(41 * 60_000)).toBe('41m');
  });

  it('counts a long run in hours and minutes, so an eleven-hour run is read at a glance', () => {
    expect(describeRunLength(11 * 3_600_000 + 6 * 60_000)).toBe('11h 6m');
  });

  it('says a run under a minute is under a minute, never nothing', () => {
    expect(describeRunLength(12_000)).toBe('< 1m');
  });

  it('says a run of no length at all is under a minute, as one event is still a run', () => {
    expect(describeRunLength(0)).toBe('< 1m');
  });
});

describe('describeStarted', () => {
  it('shows the UTC day and time, so a row and the span it sits in count the same days', () => {
    expect(describeStarted('2026-09-14T09:00:00+00:00')).toBe('2026-09-14 09:00');
  });
});

describe('the words for what a row does not carry', () => {
  it('says a run with no origin remote has no Repository, which is not the same as not knowing', () => {
    expect(noRepository).toBe('None');
    expect(notKnown).not.toBe(noRepository);
  });

  it('marks a Measure that fell short with a dash, never a zero, and gives the dash one alphabet', () => {
    expect(measureWords.fellShort).toBe('—');
    expect(measureSymbols).toEqual({ alphabet: 'condition', glyphs: ['—'] });
  });
});

describe('nextOrder', () => {
  it('leaves the direction to the answer on a column not yet sorted on', () => {
    expect(nextOrder({ sort: 'started', descending: true }, 'faults')).toEqual({ sort: 'faults', descending: null });
  });

  it('turns a column round on a second click, so both ways are one click apart', () => {
    expect(nextOrder({ sort: 'faults', descending: true }, 'faults')).toEqual({ sort: 'faults', descending: false });
    expect(nextOrder({ sort: 'faults', descending: false }, 'faults')).toEqual({ sort: 'faults', descending: true });
  });

  it('leaves the direction to the answer before one has arrived', () => {
    expect(nextOrder(null, 'cost')).toEqual({ sort: 'cost', descending: null });
  });

  it('opens on the started column with the direction left to the answer', () => {
    expect(opensOn).toEqual({ sort: 'started', descending: null });
  });
});

describe('the order in the address bar', () => {
  it('reads a column and a direction a link named', () => {
    expect(readOrder(new URLSearchParams('sort=cost&descending=false'))).toEqual({ sort: 'cost', descending: false });
  });

  it('leaves the direction to the answer when a link names only a column', () => {
    expect(readOrder(new URLSearchParams('sort=faults'))).toEqual({ sort: 'faults', descending: null });
  });

  it('opens on the started column when the address bar names none', () => {
    expect(readOrder(new URLSearchParams(''))).toEqual(opensOn);
  });

  it('falls back to the started column when the address bar names one the table lacks', () => {
    expect(readOrder(new URLSearchParams('sort=weather')).sort).toBe('started');
  });

  it('writes the same parameters the API takes, so the address shows what was asked', () => {
    const written = withOrder(new URLSearchParams(''), { sort: 'cost', descending: true });

    expect(written.toString()).toBe('sort=cost&descending=true');
  });

  it('leaves the opening order out, so an untouched table has a clean address to share', () => {
    expect(withOrder(new URLSearchParams('sort=cost&descending=true'), opensOn).toString()).toBe('');
  });

  it('keeps the parameters it was given, so sorting never throws a filter away', () => {
    const written = withOrder(new URLSearchParams('repository=acme%2Fxi'), { sort: 'cost', descending: null });

    expect(written.toString()).toBe('repository=acme%2Fxi&sort=cost');
  });
});

describe('sessionColumns', () => {
  it('names every column the table sorts on, in the order they are read', () => {
    expect(sessionColumns.map((column) => column.sort)).toEqual([
      'started',
      'repository',
      'person',
      'name',
      'length',
      'toolCalls',
      'cost',
      'faults',
    ]);
  });

  it('heads the name column Session and the count of calls Tool calls', () => {
    const headings = new Map(sessionColumns.map((column) => [column.sort, column.heading]));

    expect(headings.get('name')).toBe('Session');
    expect(headings.get('toolCalls')).toBe('Tool calls');
  });

  it('gives the two order marks an alphabet of their own', () => {
    expect(sortSymbols).toEqual({ alphabet: 'order', glyphs: [sortGlyphs.ascending, sortGlyphs.descending] });
  });
});

describe('describeSpan', () => {
  it('names both ends of the period the table covers', () => {
    expect(describeSpan(head.span)).toBe('2026-09-09 to 2026-09-15');
  });

  it('names one day once', () => {
    expect(describeSpan({ ...head.span, from: '2026-09-14', to: '2026-09-14' })).toBe('2026-09-14');
  });
});

describe('describePeriod', () => {
  it('says the answer covers the lookback, and which days that was', () => {
    expect(describePeriod(head.span, null)).toBe('The lookback, 2026-09-09 to 2026-09-15');
  });

  it('names the days alone when a span was asked for', () => {
    const span = { ...head.span, from: '2026-09-13', to: '2026-09-14', lookback: false };

    expect(describePeriod(span, { from: '2026-09-13', to: '2026-09-14' })).toBe('2026-09-13 to 2026-09-14');
  });

  it('says the lookback before an answer lands when no span was asked for', () => {
    expect(describePeriod(null, null)).toBe('The lookback');
  });

  it('names the asked days before an answer lands, so a narrowed table never claims the lookback', () => {
    expect(describePeriod(null, { from: '2026-09-13', to: '2026-09-14' })).toBe('2026-09-13 to 2026-09-14');
  });
});

describe('describeNoSessions', () => {
  it('calls an empty unnarrowed table a quiet period', () => {
    expect(describeNoSessions(everything)).toBe('No runs in this period.');
  });

  it('calls a table narrowed only by a span a quiet period too, as the span is the period', () => {
    expect(describeNoSessions({ ...everything, from: '2026-09-13', to: '2026-09-14' })).toBe('No runs in this period.');
  });

  it('says a table narrowed by a Repository, a Skill or a Depth matched nothing, never reading as a blank page', () => {
    expect(describeNoSessions({ ...everything, repository: 'acme/nu' })).toBe('No runs match this filter.');
    expect(describeNoSessions({ ...everything, skill: 'tdd' })).toBe('No runs match this filter.');
    expect(describeNoSessions({ ...everything, depth: 'full' })).toBe('No runs match this filter.');
  });

  it('calls a quiet period quiet when the address bar names a Depth nobody has', () => {
    // The API lists both depths for a Depth it cannot read, so nothing was narrowed away.
    expect(describeNoSessions({ ...everything, depth: 'deep' })).toBe('No runs in this period.');
  });
});
