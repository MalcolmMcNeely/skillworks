import { describe, expect, it } from 'vitest';
import { activationPath, activationsPath, describeRecorded, skillsPath } from './activations';

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

describe('describeRecorded', () => {
  it('shows what was recorded', () => {
    expect(describeRecorded('acme/xi')).toBe('acme/xi');
  });

  it('says so in words when the event never recorded it', () => {
    expect(describeRecorded(null)).toBe('Not recorded');
    expect(describeRecorded('')).toBe('Not recorded');
  });
});
