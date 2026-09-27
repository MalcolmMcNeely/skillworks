import { describe, expect, it } from 'vitest';
import { namedIn, noFindingsWord, type Finding, type FindingKind, type FindingsPage } from './findings';

const finding = (kind: FindingKind, figure: number | null, over: Partial<Finding> = {}): Finding => ({
  kind,
  subject: null,
  figure,
  bar: 3,
  step: null,
  atUtc: '2026-09-14T09:00:00.000Z',
  lengthMs: 5_000,
  ...over,
});

const page = (findings: Finding[]): FindingsPage => ({ kind: 'findings', findings });

describe('namedIn', () => {
  it('names nothing where a run crossed no bar', () => {
    expect(namedIn(page([]))).toEqual([]);
  });

  it('names nothing before the findings have landed', () => {
    expect(namedIn(null)).toEqual([]);
  });

  // A reader who learned the list on one run should find the same finding in the same place on the next.
  it('keeps the findings in one order whatever order they arrive in', () => {
    const named = namedIn(page([finding('waiting', 180_000), finding('rateLimited', 2), finding('editedAgain', 6)]));

    expect(named.map((each) => each.kind)).toEqual(['editedAgain', 'rateLimited', 'waiting']);
  });

  it('reads a count of tries as a count', () => {
    expect(namedIn(page([finding('failingAgain', 4)]))[0].reading).toBe('4 times');
  });

  // Both the rate limit and the cache rebuild cross on one, so "1 times" would be the everyday reading.
  it('reads a count of one as a word rather than as one times', () => {
    expect(namedIn(page([finding('rateLimited', 1)]))[0].reading).toBe('once');
  });

  it('reads a share as a percentage', () => {
    expect(namedIn(page([finding('hooks', 0.22)]))[0].reading).toBe('22%');
  });

  it('reads a wait as a length of time', () => {
    expect(namedIn(page([finding('waiting', 185_000)]))[0].reading).toBe('3m 05s');
  });

  it('reads a cost against siblings as a multiple of what they cost', () => {
    expect(namedIn(page([finding('costlySubagent', 4.15)]))[0].reading).toBe('4.2× the others');
  });

  // Read as a zero it would say the run was clean, which is the one thing nobody can know here.
  it('says a finding with no figure is not known, and marks it as such', () => {
    const named = namedIn(page([finding('hooks', null)]))[0];

    expect(named.reading).toBe('Not known');
    expect(named.known).toBe(false);
  });

  it('measures the spell a finding happened in from its moment and its length', () => {
    const named = namedIn(page([finding('waiting', 180_000, { lengthMs: 180_000 })]))[0];

    expect(named.startMs).toBe(Date.parse('2026-09-14T09:00:00.000Z'));
    expect(named.endMs).toBe(named.startMs + 180_000);
  });

  // How close the call was needs both figures, and each reads in the units of its own bar.
  it('reads the bar in the same words as the figure it was crossed on', () => {
    expect(namedIn(page([finding('hooks', 0.22, { bar: 0.15 })]))[0].barReading).toBe('15%');
    expect(namedIn(page([finding('waiting', 185_000, { bar: 120_000 })]))[0].barReading).toBe('2m 00s');
  });

  it('reads the bar of a finding nobody could measure, which is the one thing about it that is known', () => {
    expect(namedIn(page([finding('costlySubagent', null, { bar: 3 })]))[0].barReading).toBe('3.0× the others');
  });
});

describe('noFindingsWord', () => {
  it('says a run whose spans have not landed is still being read', () => {
    expect(noFindingsWord(null)).toBe('Still reading the run.');
  });

  it('says a run that crossed no bar crossed none', () => {
    expect(noFindingsWord(page([]))).toBe('Nothing in this run crossed a bar.');
  });
});
