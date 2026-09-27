import { describe, expect, it } from 'vitest';
import { namedIn, type Finding } from './findings';
import { momentOf } from './moment';
import { showInTimeline } from './showInTimeline';
import type { Spell } from '../timeline/view';

const at = (clock: string) => Date.parse(`2026-09-14T${clock}.000Z`);

const finding: Finding = {
  kind: 'failingAgain',
  subject: 'npm test',
  figure: 4,
  bar: 3,
  step: '3',
  atUtc: '2026-09-14T10:00:00.000Z',
  lengthMs: 60_000,
};

const nameOf = (over: Partial<Finding> = {}) => namedIn({ kind: 'findings', findings: [{ ...finding, ...over }] })[0];

const whole: Spell = [at('09:00:00'), at('11:00:00')];

describe('showInTimeline', () => {
  it('shows a View around the moment the Finding happened in', () => {
    const named = nameOf();

    const { view } = showInTimeline(named, whole);

    expect(view[0]).toBeLessThan(named.startMs);
    expect(view[1]).toBeGreaterThan(named.endMs);
    expect(view[0]).toBeGreaterThan(whole[0]);
    expect(view[1]).toBeLessThan(whole[1]);
  });

  it('keeps the View inside the run', () => {
    expect(showInTimeline(nameOf({ atUtc: '2026-09-14T09:00:00.000Z' }), whole).view[0]).toBe(whole[0]);
  });

  it('shows the same View the Finding card draws', () => {
    const named = nameOf();

    expect(showInTimeline(named, whole).view).toEqual(momentOf(named, [], whole).spell);
  });

  it('opens the Step the Finding names', () => {
    expect(showInTimeline(nameOf(), whole).step).toBe('3');
  });

  it('opens no Step for a Finding about a length of time, so a Step left open does not stay open', () => {
    expect(showInTimeline(nameOf({ kind: 'waiting', step: null }), whole).step).toBeNull();
  });
});
