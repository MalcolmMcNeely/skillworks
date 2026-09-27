import { describe, expect, it } from 'vitest';
import { everything } from '../../shared/filters/lib/filters';
import {
  describeNoSessions,
  describeQuiet,
  describeRunLength,
  describeStarted,
  failSessionsRead,
  foldSessionsLine,
  laterShortfall,
  listFilter,
  loadMore,
  lookFurtherBack,
  measureSymbols,
  measureWords,
  nextRead,
  noRepository,
  notKnown,
  readOn,
  rowParams,
  sessionHeadings,
  type MeasureName,
  type SessionRow,
  type SessionsAnswer,
  type SessionsHead,
  type SessionsLine,
} from './sessions';

const head: SessionsHead = { kind: 'head', asOfUtc: '2026-09-15T12:00:00+00:00' };

const run: SessionRow = {
  id: '8f1c0a9e-0000-4000-8000-000000000001',
  startedUtc: '2026-09-13T22:00:00+00:00',
  repository: 'malcolmania/skillworks',
  person: 'ada@acme.test',
  name: 'Fixing the failing build',
  lengthMs: 2_460_000,
  running: false,
  latestUtc: '2026-09-14T09:00:00+00:00',
  firstDay: '2026-09-13',
  lastDay: '2026-09-14',
};

const other: SessionRow = { ...run, id: '8f1c0a9e-0000-4000-8000-000000000002', name: 'Reading the logs' };

const complete = { kind: 'complete', missing: null } as const;

const oldestLatest = '2026-09-14T09:00:00+00:00';

function withRows(...sessions: SessionRow[]): SessionsAnswer {
  return foldSessionsLine(foldSessionsLine(null, head), { kind: 'sessions', sessions });
}

function endOn(latest: string | null): SessionsLine {
  return { kind: 'end', gap: complete, oldestLatestUtc: latest, quietSinceUtc: null };
}

function cell(answer: SessionsAnswer, measure: MeasureName, id: string = run.id) {
  return answer.rows.find((row) => row.session.id === id)?.measures[measure];
}

function depthOf(answer: SessionsAnswer, id: string = run.id) {
  return answer.rows.find((row) => row.session.id === id)?.depth;
}

function withMeasures(answer: SessionsAnswer, ...measures: MeasureName[]): SessionsAnswer {
  return measures.reduce(
    (folded, measure) => foldSessionsLine(folded, { kind: 'measure', measure, values: {} }),
    answer,
  );
}

describe('foldSessionsLine', () => {
  it('opens on the instant it reads up to and no rows, so the page shows the Arriving state before they land', () => {
    const answer = foldSessionsLine(null, head);

    expect(answer).toEqual({
      asOfUtc: head.asOfUtc,
      rows: [],
      landed: false,
      arriving: true,
      gap: null,
      oldestLatestUtc: null,
      quietSinceUtc: null,
      held: 0,
    });
  });

  it('takes the rows from the sessions line and marks them landed, so the table draws before the answer ends', () => {
    const answer = withRows(run);

    expect(answer.rows.map((row) => row.session)).toEqual([run]);
    expect(answer.landed).toBe(true);
    expect(answer.arriving).toBe(true);
  });

  it('keeps the rows in the order the answer sent them, which is the newest work first', () => {
    expect(withRows(other, run).rows.map((row) => row.session.id)).toEqual([other.id, run.id]);
  });

  it('marks an answer with no runs landed too, so an empty list is told apart from rows still to come', () => {
    const answer = withRows();

    expect(answer.landed).toBe(true);
    expect(answer.rows).toEqual([]);
  });

  it('ends the answer and keeps its gap, so a screen knows the rows are all there are', () => {
    const answer = foldSessionsLine(withRows(run), endOn(oldestLatest));

    expect(answer.arriving).toBe(false);
    expect(answer.gap).toEqual(complete);
    expect(answer.rows.map((row) => row.session)).toEqual([run]);
  });

  it('keeps the Latest of the oldest row the end names, so the next read can start where this one stopped', () => {
    const answer = foldSessionsLine(withRows(run), endOn(oldestLatest));

    expect(answer.oldestLatestUtc).toBe(oldestLatest);
  });

  it('holds no Latest while the answer is arriving, as only the end says where the read stopped', () => {
    expect(withRows(run).oldestLatestUtc).toBeNull();
  });

  it('stays arriving through its rows and its Measures, so it is complete only once the end line lands', () => {
    const opened = foldSessionsLine(null, head);
    const drawn = foldSessionsLine(opened, { kind: 'sessions', sessions: [run] });
    const measured = withMeasures(drawn, 'cost');

    expect([opened.arriving, drawn.arriving, measured.arriving]).toEqual([true, true, true]);
    expect(foldSessionsLine(measured, endOn(null)).arriving).toBe(false);
  });

  it('refuses a line before the head, as a row with no as-of instant cannot be placed', () => {
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
    const answer = foldSessionsLine(landed, {
      kind: 'end',
      gap: { kind: 'unreachable', missing: 'Tool calls' },
      oldestLatestUtc: oldestLatest,
      quietSinceUtc: null,
    });

    expect(cell(answer, 'toolCalls')).toEqual({ state: 'fellShort' });
    expect(cell(answer, 'cost')).toEqual({ state: 'landed', value: 1.25 });
  });

  it('tells a Measure that read as nought from one the Gap names, so a dash is never a zero', () => {
    const nought = foldSessionsLine(withRows(run), { kind: 'measure', measure: 'cost', values: {} });
    const answer = foldSessionsLine(nought, {
      kind: 'end',
      gap: { kind: 'unreachable', missing: 'Tool calls' },
      oldestLatestUtc: oldestLatest,
      quietSinceUtc: null,
    });

    expect(cell(answer, 'cost')).toEqual({ state: 'landed', value: 0 });
    expect(cell(answer, 'toolCalls')).toEqual({ state: 'fellShort' });
  });
});

describe('the Depth on a folded answer', () => {
  it('leaves the Depth of a fresh row arriving, so a cell nobody has read yet is blank', () => {
    expect(depthOf(withRows(run))).toEqual({ state: 'arriving' });
  });

  it('lands each Depth the line of Depths names on its row', () => {
    const answer = foldSessionsLine(withRows(run, other), {
      kind: 'depths',
      depths: { [run.id]: 'full', [other.id]: 'thin' },
    });

    expect(depthOf(answer)).toEqual({ state: 'landed', value: 'full' });
    expect(depthOf(answer, other.id)).toEqual({ state: 'landed', value: 'thin' });
  });

  it('reads a row the line of Depths does not name as a dash, never as Thin', () => {
    const answer = foldSessionsLine(withRows(run, other), { kind: 'depths', depths: { [run.id]: 'full' } });

    expect(depthOf(answer, other.id)).toEqual({ state: 'fellShort' });
  });

  it('reads a Depth that never came as a dash once the answer ends', () => {
    expect(depthOf(foldSessionsLine(withRows(run), endOn(null)))).toEqual({ state: 'fellShort' });
  });

  it('lands a later line of Depths on the new rows alone, so a row held from before keeps its own', () => {
    const first = foldSessionsLine(
      foldSessionsLine(withRows(run), { kind: 'depths', depths: { [run.id]: 'full' } }),
      endOn(oldestLatest),
    );
    const drawn = foldSessionsLine(foldSessionsLine(first, head), { kind: 'sessions', sessions: [other] });
    const answer = foldSessionsLine(drawn, { kind: 'depths', depths: { [other.id]: 'thin' } });

    expect(depthOf(answer)).toEqual({ state: 'landed', value: 'full' });
    expect(depthOf(answer, other.id)).toEqual({ state: 'landed', value: 'thin' });
  });

  it('stays arriving through its line of Depths, as only the end line says the answer is whole', () => {
    expect(foldSessionsLine(withRows(run), { kind: 'depths', depths: {} }).arriving).toBe(true);
  });
});

describe('a later read folded into the rows held', () => {
  const unreachable = { kind: 'unreachable', missing: 'The events store answered 503.' } as const;

  function ended(answer: SessionsAnswer, latest: string | null = oldestLatest): SessionsAnswer {
    return foldSessionsLine(answer, endOn(latest));
  }

  function later(answer: SessionsAnswer): SessionsAnswer {
    return foldSessionsLine(answer, head);
  }

  it('appends the rows of a second read to the rows already held', () => {
    const answer = foldSessionsLine(later(ended(withRows(run))), { kind: 'sessions', sessions: [other] });

    expect(answer.rows.map((row) => row.session.id)).toEqual([run.id, other.id]);
  });

  it('keeps the rows already held while the later read is in flight', () => {
    const answer = later(ended(withRows(run)));

    expect(answer.rows.map((row) => row.session)).toEqual([run]);
    expect(answer.arriving).toBe(true);
    expect(loadMore(answer)).toBe('arriving');
  });

  it('lands a later Measure on the new rows alone, so a row held from before never reads as a zero', () => {
    const first = ended(foldSessionsLine(withRows(run), { kind: 'measure', measure: 'cost', values: { [run.id]: 1.25 } }));
    const drawn = foldSessionsLine(later(first), { kind: 'sessions', sessions: [other] });
    const answer = foldSessionsLine(drawn, { kind: 'measure', measure: 'cost', values: { [other.id]: 2 } });

    expect(cell(answer, 'cost', run.id)).toEqual({ state: 'landed', value: 1.25 });
    expect(cell(answer, 'cost', other.id)).toEqual({ state: 'landed', value: 2 });
  });

  it('takes the Latest the later read ended on, so the next click reads on from there', () => {
    const drawn = foldSessionsLine(later(ended(withRows(run))), { kind: 'sessions', sessions: [other] });

    expect(ended(drawn, '2026-09-13T08:00:00+00:00').oldestLatestUtc).toBe('2026-09-13T08:00:00+00:00');
  });

  it('keeps the rows and the button when the later read ends on a store that did not answer', () => {
    const failed = foldSessionsLine(later(ended(withRows(run))), {
      kind: 'end',
      gap: unreachable,
      oldestLatestUtc: null,
      quietSinceUtc: null,
    });

    expect(failed.rows.map((row) => row.session)).toEqual([run]);
    expect(failed.gap).toEqual(unreachable);
    expect(failed.oldestLatestUtc).toBe(oldestLatest);
    expect(loadMore(failed)).toBe('ready');
    expect(laterShortfall(failed)).toEqual(unreachable);
  });

  it('puts no shortfall under the rows for a first read, as the head already names it', () => {
    const failed = foldSessionsLine(withRows(run), { kind: 'end', gap: unreachable, oldestLatestUtc: oldestLatest, quietSinceUtc: null });

    expect(laterShortfall(failed)).toBeNull();
  });

  it('keeps the rows and the button when the later read breaks off before its end', () => {
    const broken = foldSessionsLine(later(ended(withRows(run))), { kind: 'sessions', sessions: [other] });
    const failed = failSessionsRead(broken, 'Studio could not reach its API.');

    expect(failed.rows.map((row) => row.session.id)).toEqual([run.id, other.id]);
    expect(cell(failed, 'cost', other.id)).toEqual({ state: 'fellShort' });
    expect(failed.gap).toEqual({ kind: 'unreachable', missing: 'Studio could not reach its API.' });
    expect(failed.arriving).toBe(false);
    expect(loadMore(failed)).toBe('ready');
  });
});

describe('loadMore', () => {
  it('offers the button once a read has ended on a Latest', () => {
    expect(loadMore(foldSessionsLine(withRows(run), endOn(oldestLatest)))).toBe('ready');
  });

  it('hides the button while the first read is in flight, as no Latest is known yet', () => {
    expect(loadMore(withRows(run))).toBe('hidden');
  });

  it('hides the button when the read ended on no Latest', () => {
    expect(loadMore(foldSessionsLine(withRows(run), endOn(null)))).toBe('hidden');
  });
});

describe('a read that ends on a quiet 30 days', () => {
  const quietSince = '2026-08-16T12:00:00+00:00';

  function quiet(answer: SessionsAnswer): SessionsAnswer {
    return foldSessionsLine(answer, { kind: 'end', gap: complete, oldestLatestUtc: null, quietSinceUtc: quietSince });
  }

  it('keeps the quiet date the end names', () => {
    expect(quiet(withRows(run)).quietSinceUtc).toBe(quietSince);
  });

  it('says there are no older Prompts back to that date, never that the store holds no more', () => {
    expect(describeQuiet(quiet(withRows(run)))).toBe('No older Prompts back to 2026-08-16.');
  });

  it('says nothing about a quiet period while the read ended on a Latest', () => {
    expect(describeQuiet(foldSessionsLine(withRows(run), endOn(oldestLatest)))).toBeNull();
  });

  it('hides Load more and offers Look further back after a quiet end', () => {
    const answer = quiet(withRows(run));

    expect(loadMore(answer)).toBe('hidden');
    expect(lookFurtherBack(answer)).toBe('ready');
  });

  it('offers no Look further back while the read ended on a Latest', () => {
    expect(lookFurtherBack(foldSessionsLine(withRows(run), endOn(oldestLatest)))).toBe('hidden');
  });

  it('starts the further read from the quiet date, on the same as-of instant', () => {
    expect(nextRead(quiet(withRows(run)))).toEqual({ asOfUtc: head.asOfUtc, latestBeforeUtc: quietSince });
  });

  it('lets either button read on once the read has ended, and neither while it is in flight', () => {
    expect(readOn(quiet(withRows(run)))).toBe('ready');
    expect(readOn(foldSessionsLine(withRows(run), endOn(oldestLatest)))).toBe('ready');
    expect(readOn(foldSessionsLine(quiet(withRows(run)), head))).toBe('arriving');
    expect(readOn(withRows(run))).toBe('hidden');
  });

  it('starts a later read from the Latest of the oldest row', () => {
    expect(nextRead(foldSessionsLine(withRows(run), endOn(oldestLatest)))).toEqual({
      asOfUtc: head.asOfUtc,
      latestBeforeUtc: oldestLatest,
    });
  });

  it('holds the quiet date and shows the button busy while the further read is in flight', () => {
    const answer = foldSessionsLine(quiet(withRows(run)), head);

    expect(lookFurtherBack(answer)).toBe('arriving');
    expect(describeQuiet(answer)).toBeNull();
  });

  it('keeps the quiet date and the button when the further read ends on a store that did not answer', () => {
    const failed = foldSessionsLine(foldSessionsLine(quiet(withRows(run)), head), {
      kind: 'end',
      gap: { kind: 'unreachable', missing: 'The events store answered 503.' },
      oldestLatestUtc: null,
      quietSinceUtc: null,
    });

    expect(failed.quietSinceUtc).toBe(quietSince);
    expect(lookFurtherBack(failed)).toBe('ready');
    expect(loadMore(failed)).toBe('hidden');
  });

  it('takes the Latest a further read ended on, and drops the quiet date it started from', () => {
    const further = foldSessionsLine(foldSessionsLine(quiet(withRows(run)), head), {
      kind: 'sessions',
      sessions: [other],
    });
    const answer = foldSessionsLine(further, endOn('2026-08-10T08:00:00+00:00'));

    expect(answer.rows.map((row) => row.session.id)).toEqual([run.id, other.id]);
    expect(loadMore(answer)).toBe('ready');
    expect(lookFurtherBack(answer)).toBe('hidden');
  });

  it('offers Look further back when the end also carries a Gap that is not the read failing', () => {
    const answer = foldSessionsLine(withRows(run), {
      kind: 'end',
      gap: { kind: 'unreachable', missing: 'Tool calls' },
      oldestLatestUtc: null,
      quietSinceUtc: quietSince,
    });

    expect(lookFurtherBack(answer)).toBe('ready');
    expect(loadMore(answer)).toBe('hidden');
  });
});

describe('rowParams', () => {
  it('opens a row on the days it covers, so the Session page reads the whole of its work', () => {
    expect(rowParams(run, everything).toString()).toBe('from=2026-09-13&to=2026-09-14');
  });

  it('keeps the rest of the Filter and puts the row days in place of any span, so going up lands on the same list', () => {
    const filter = { ...everything, from: '2026-09-01', to: '2026-09-02', repository: 'acme/xi' };

    expect(rowParams(run, filter).toString()).toBe('from=2026-09-13&to=2026-09-14&repository=acme%2Fxi');
  });
});

describe('listFilter', () => {
  it('leaves a span an old link carries off the question, as no span narrows the list', () => {
    const filter = { ...everything, from: '2026-09-01', to: '2026-09-07', skill: 'tdd' };

    expect(listFilter(filter)).toEqual({ ...everything, skill: 'tdd' });
  });
});

describe('sessionHeadings', () => {
  it('heads every column a row carries, in the order they are read', () => {
    expect(sessionHeadings).toEqual([
      'Started',
      'Repository',
      'Person',
      'Session',
      'Length',
      'Depth',
      'Tool calls',
      'Cost',
      'Faults',
    ]);
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
  it('shows the UTC day and time, so a row and the days it covers count the same days', () => {
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

describe('describeNoSessions', () => {
  function quietBackTo(answer: SessionsAnswer, quietSinceUtc: string): SessionsAnswer {
    return foldSessionsLine(answer, { kind: 'end', gap: complete, oldestLatestUtc: null, quietSinceUtc });
  }

  const empty = quietBackTo(withRows(), '2026-08-16T12:00:00+00:00');

  it('says an empty unnarrowed list found nothing in the 30 days one read looks back', () => {
    expect(describeNoSessions(everything, empty)).toBe('No runs in the last 30 days.');
  });

  it('says how far back the list has looked once it has looked further back', () => {
    const further = quietBackTo(foldSessionsLine(empty, head), '2026-07-17T12:00:00+00:00');

    expect(describeNoSessions(everything, further)).toBe('No runs in the last 60 days.');
  });

  it('keeps the days already looked back while a further read is in flight', () => {
    expect(describeNoSessions(everything, foldSessionsLine(empty, head))).toBe('No runs in the last 30 days.');
  });

  it('says a list narrowed by a Repository or a Skill matched nothing, never reading as a blank page', () => {
    expect(describeNoSessions({ ...everything, repository: 'acme/nu' }, empty)).toBe('No runs match this filter.');
    expect(describeNoSessions({ ...everything, skill: 'tdd' }, empty)).toBe('No runs match this filter.');
  });
});
