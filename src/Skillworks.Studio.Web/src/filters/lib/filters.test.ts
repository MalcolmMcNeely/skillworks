import { describe, expect, it } from 'vitest';
import {
  describeEmpty,
  describeFilter,
  everything,
  filterParams,
  filterQuery,
  isEverything,
  readFilter,
  withChosen,
  type Filter,
} from './filters';

const narrowed: Filter = {
  from: '2026-09-01',
  to: '2026-09-05',
  repository: 'skillworks',
  skill: 'grilling',
};

describe('filterQuery', () => {
  it('asks for nothing when nothing is narrowed', () => {
    expect(filterQuery(everything)).toBe('');
  });

  it('leaves out the parts that are not narrowed', () => {
    expect(filterQuery({ ...everything, repository: 'skillworks' })).toBe('?repository=skillworks');
  });

  it('carries all three filters at once', () => {
    expect(filterQuery(narrowed)).toBe(
      '?from=2026-09-01&to=2026-09-05&repository=skillworks&skill=grilling',
    );
  });

  it('escapes a skill name that a query string would otherwise read as two', () => {
    expect(filterQuery({ ...everything, skill: 'probekit:probe local' })).toBe(
      '?skill=probekit%3Aprobe+local',
    );
  });
});

describe('readFilter', () => {
  it('reads back what it wrote, so a reload lands on the same view', () => {
    expect(readFilter(filterParams(narrowed))).toEqual(narrowed);
  });

  it('treats a parameter that is not there as not narrowed', () => {
    expect(readFilter(new URLSearchParams('repository=skillworks'))).toEqual({
      ...everything,
      repository: 'skillworks',
    });
  });
});

describe('isEverything', () => {
  it('is true only when no part is narrowed', () => {
    expect(isEverything(everything)).toBe(true);
    expect(isEverything({ ...everything, skill: 'grilling' })).toBe(false);
  });
});

describe('describeFilter', () => {
  it('names both ends of a range', () => {
    expect(describeFilter({ ...everything, from: '2026-09-01', to: '2026-09-05' })).toBe(
      '2026-09-01 to 2026-09-05',
    );
  });

  it('names one end when only one was given', () => {
    expect(describeFilter({ ...everything, from: '2026-09-01' })).toBe('from 2026-09-01');
    expect(describeFilter({ ...everything, to: '2026-09-05' })).toBe('up to 2026-09-05');
  });

  it('names all three in the order they are asked', () => {
    expect(describeFilter(narrowed)).toBe('2026-09-01 to 2026-09-05, in skillworks, grilling');
  });
});

describe('describeEmpty', () => {
  it('reads an empty filtered table as an answer rather than a failure', () => {
    expect(describeEmpty({ ...everything, repository: 'skillworks' })).toBe(
      'Nothing matched in skillworks.',
    );
  });

  it('says the history is empty when nothing was narrowed at all', () => {
    expect(describeEmpty(everything)).toBe('No skill has fired yet.');
  });

  it('names the missing source instead, when there is one', () => {
    expect(describeEmpty(everything, 'There is no folder at /home/me/.claude/projects.')).toBe(
      'There is no folder at /home/me/.claude/projects.',
    );
  });

  it('blames the missing source rather than the filter, so nobody widens a date range for nothing', () => {
    expect(describeEmpty(narrowed, 'There is no folder at /home/me/.claude/projects.')).toBe(
      'There is no folder at /home/me/.claude/projects.',
    );
  });
});

describe('withChosen', () => {
  it('offers the choices as they came', () => {
    expect(withChosen(['alpha', 'beta'], 'alpha')).toEqual(['alpha', 'beta']);
  });

  it('keeps a choice the list has not got, so the chooser never shows the wrong one', () => {
    expect(withChosen(['alpha'], 'gamma')).toEqual(['gamma', 'alpha']);
  });

  it('adds nothing when nothing is chosen', () => {
    expect(withChosen(['alpha'], '')).toEqual(['alpha']);
  });
});
