import { describe, expect, it } from 'vitest';
import {
  describeLength,
  describeSpan,
  describeStarted,
  foldSessionsLine,
  noRepository,
  notKnown,
  type Session,
  type SessionsHead,
} from './sessions';

const head: SessionsHead = {
  kind: 'head',
  span: { from: '2026-09-09', to: '2026-09-15', lookback: true, fromUtc: '2026-09-09T00:00:00+00:00', untilUtc: '2026-09-16T00:00:00+00:00' },
};

const run: Session = {
  id: '8f1c0a9e-0000-4000-8000-000000000001',
  startedUtc: '2026-09-14T09:00:00+00:00',
  repository: 'malcolmania/skillworks',
  person: 'ada@acme.test',
  name: 'Fixing the failing build',
  lengthMs: 2_460_000,
  running: false,
};

describe('foldSessionsLine', () => {
  it('opens on the span and no rows, so the page says which days it covers before they land', () => {
    const answer = foldSessionsLine(null, head);

    expect(answer).toEqual({ span: head.span, sessions: [], landed: false, arriving: true, gap: null });
  });

  it('takes the rows from the sessions line and marks them landed, so the table draws before the answer ends', () => {
    const answer = foldSessionsLine(foldSessionsLine(null, head), { kind: 'sessions', sessions: [run] });

    expect(answer.sessions).toEqual([run]);
    expect(answer.landed).toBe(true);
    expect(answer.arriving).toBe(true);
  });

  it('marks an answer with no runs landed too, so an empty week is told apart from rows still to come', () => {
    const answer = foldSessionsLine(foldSessionsLine(null, head), { kind: 'sessions', sessions: [] });

    expect(answer.landed).toBe(true);
    expect(answer.sessions).toEqual([]);
  });

  it('ends the answer and keeps its gap, so a screen knows the rows are all there are', () => {
    const landed = foldSessionsLine(foldSessionsLine(null, head), { kind: 'sessions', sessions: [run] });
    const answer = foldSessionsLine(landed, { kind: 'end', gap: { kind: 'complete', missing: null } });

    expect(answer.arriving).toBe(false);
    expect(answer.gap).toEqual({ kind: 'complete', missing: null });
    expect(answer.sessions).toEqual([run]);
  });

  it('refuses a line before the head, as a row with no span says nothing about the period', () => {
    expect(() => foldSessionsLine(null, { kind: 'sessions', sessions: [run] })).toThrow(
      'A sessions answer starts with its head, not a sessions line.',
    );
  });
});

describe('describeLength', () => {
  it('counts a short run in minutes', () => {
    expect(describeLength(41 * 60_000)).toBe('41m');
  });

  it('counts a long run in hours and minutes, so an eleven-hour run is read at a glance', () => {
    expect(describeLength(11 * 3_600_000 + 6 * 60_000)).toBe('11h 6m');
  });

  it('says a run under a minute is under a minute, never nothing', () => {
    expect(describeLength(12_000)).toBe('< 1m');
  });

  it('says a run of no length at all is under a minute, as one event is still a run', () => {
    expect(describeLength(0)).toBe('< 1m');
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
});

describe('describeSpan', () => {
  it('names both ends of the period the table covers', () => {
    expect(describeSpan(head.span)).toBe('2026-09-09 to 2026-09-15');
  });

  it('names one day once', () => {
    expect(describeSpan({ ...head.span, from: '2026-09-14', to: '2026-09-14' })).toBe('2026-09-14');
  });
});
