import { describe, expect, it } from 'vitest';
import {
  describeDay,
  everything,
  filterParams,
  filterQuery,
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

describe('describeDay', () => {
  it('names a UTC day by its date and month, short enough for a HUD', () => {
    expect(describeDay('2026-09-05')).toBe('05 Sep');
    expect(describeDay('2026-12-31')).toBe('31 Dec');
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
