import { describe, expect, it } from 'vitest';
import { activationPath, activationsPath, describeMoment, describeRecorded, skillsPath } from './activations';

/** A reader who has narrowed the table and ranked it by cost. Both have to survive the round trip. */
const view = 'repository=alpha&sort=cost&desc=no';

describe('activationsPath', () => {
  it('takes the reader to the one skill they clicked', () => {
    expect(activationsPath('', 'tdd')).toBe('/skills/tdd/activations');
  });

  it('carries the whole view, sort and all, so nothing is lost on the way out', () => {
    expect(activationsPath(view, 'tdd')).toBe('/skills/tdd/activations?repository=alpha&sort=cost&desc=no');
  });

  it('keeps a skill named like a path out of the path', () => {
    expect(activationsPath('', 'probekit:probe-local')).toBe('/skills/probekit%3Aprobe-local/activations');
  });
});

describe('activationPath', () => {
  it('opens one firing and keeps the view the reader built', () => {
    expect(activationPath(view, 'toolu_1')).toBe('/activations/toolu_1?repository=alpha&sort=cost&desc=no');
  });
});

describe('skillsPath', () => {
  it('hands the reader back the table they left, sort and filter both', () => {
    expect(skillsPath(view)).toBe('/?repository=alpha&sort=cost&desc=no');
  });

  it('goes to a plain table when there was nothing to keep', () => {
    expect(skillsPath('')).toBe('/');
  });
});

describe('describeMoment', () => {
  it('reads the moment in UTC, whatever clock the reader is sitting at', () => {
    expect(describeMoment('2026-09-02T14:48:23.182+00:00')).toBe('2026-09-02 14:48:23 UTC');
  });

  it('reads an offset moment at the hour it actually happened', () => {
    expect(describeMoment('2026-09-02T16:48:23.182+02:00')).toBe('2026-09-02 14:48:23 UTC');
  });

  it('shows a moment it cannot read as it was recorded', () => {
    expect(describeMoment('not a moment')).toBe('not a moment');
  });
});

describe('describeRecorded', () => {
  it('shows what was recorded', () => {
    expect(describeRecorded('main')).toBe('main');
  });

  it('shows a dash for something the transcript never recorded', () => {
    expect(describeRecorded(null)).toBe('—');
    expect(describeRecorded('')).toBe('—');
  });
});
