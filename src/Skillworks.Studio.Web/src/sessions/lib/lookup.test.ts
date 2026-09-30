import { describe, expect, it } from 'vitest';
import { describeNoMatch, narrowByLookup } from './lookup';
import {
  foldSessionsLine,
  lookFurtherBack,
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

const other: SessionRow = { ...run, id: 'c3d2e1f0-0000-4000-8000-000000000002', name: 'Reading the logs' };

function withRows(...sessions: SessionRow[]): SessionsAnswer {
  return foldSessionsLine(foldSessionsLine(null, head), { kind: 'sessions', sessions });
}

function ids(answer: SessionsAnswer): string[] {
  return answer.rows.map((row) => row.session.id);
}

const complete = { kind: 'complete', missing: null } as const;

function endOn(latest: string | null, quietSince: string | null = null): SessionsLine {
  return { kind: 'end', gap: complete, oldestLatestUtc: latest, quietSinceUtc: quietSince };
}

describe('narrowByLookup', () => {
  it('keeps only the rows whose id starts with the text, so part of an id picks out a run', () => {
    expect(ids(narrowByLookup(withRows(run, other), '8f1c'))).toEqual([run.id]);
  });

  it('matches whatever the letter case, so an id copied in upper case still matches its row', () => {
    expect(ids(narrowByLookup(withRows(run, other), '8F1C0A9E'))).toEqual([run.id]);
  });

  it('ignores the spaces around the text, so a careless copy still matches', () => {
    expect(ids(narrowByLookup(withRows(run, other), '  c3d2 '))).toEqual([other.id]);
  });

  it('gives the whole answer back for an empty Lookup, exactly as the list was', () => {
    const answer = foldSessionsLine(withRows(run, other), endOn(run.latestUtc));

    expect(narrowByLookup(answer, '')).toEqual(answer);
    expect(narrowByLookup(answer, '   ')).toEqual(answer);
  });

  it('changes nothing but the rows, so a narrowed answer keeps its read-on state and its Gap', () => {
    const answer = foldSessionsLine(withRows(run, other), endOn(run.latestUtc));

    expect(narrowByLookup(answer, 'c3d2')).toEqual({ ...answer, rows: [answer.rows[1]] });
  });

  it('keeps Look further back after a quiet end, as narrowing the rows changes nothing about how far the list has read', () => {
    const quiet = foldSessionsLine(withRows(run), endOn(null, '2026-08-16T12:00:00+00:00'));
    const narrowed = narrowByLookup(quiet, 'zzz');

    expect(narrowed.rows).toEqual([]);
    expect(lookFurtherBack(narrowed)).toBe('ready');
    expect(narrowed.quietSinceUtc).toBe('2026-08-16T12:00:00+00:00');
  });

  it('narrows the rows a later read adds too, so a match that lands on Load more shows up', () => {
    const first = foldSessionsLine(withRows(run), endOn(run.latestUtc));
    const later = foldSessionsLine(foldSessionsLine(first, head), { kind: 'sessions', sessions: [other] });

    expect(ids(narrowByLookup(later, 'c3d2'))).toEqual([other.id]);
  });
});

describe('describeNoMatch', () => {
  it('says how many rows have been read and what none of them starts with, and points at the whole id', () => {
    expect(describeNoMatch(withRows(run, other), 'zzz')).toBe(
      'No run in the 2 rows read so far starts with zzz. Paste the whole id to look further back.',
    );
  });

  it('shows the text as it was matched, with the spaces around it gone', () => {
    expect(describeNoMatch(withRows(run), ' ab ')).toBe(
      'No run in the 1 rows read so far starts with ab. Paste the whole id to look further back.',
    );
  });

  it('says nothing while the Lookup is empty, as nothing has been narrowed away', () => {
    expect(describeNoMatch(withRows(run), '')).toBeNull();
    expect(describeNoMatch(withRows(run), '  ')).toBeNull();
  });
});
