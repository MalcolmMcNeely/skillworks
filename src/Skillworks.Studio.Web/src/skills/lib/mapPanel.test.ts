import { describe, expect, it } from 'vitest';
import type { Gap } from '../../gaps/lib/gaps';
import { mapPanelOf } from './mapPanel';
import type { SkillSummary } from './skills';

const noTokens = { inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, cacheCreationTokens: 0 };

const fired: SkillSummary = {
  name: 'grilling',
  activations: 3,
  repositories: [],
  models: [],
  efforts: [],
  spend: { ...noTokens, cost: 0.3 },
  each: 0.1,
  origins: [],
};

const neverFired: SkillSummary = { ...fired, name: 'tdd', activations: 0, each: null, spend: { ...noTokens, cost: 0 } };

const complete: Gap = { kind: 'complete', missing: null };

function wordOf(panel: ReturnType<typeof mapPanelOf>): string | undefined {
  return panel?.word;
}

describe('mapPanelOf', () => {
  it('shows no panel once there are tiles to show', () => {
    expect(mapPanelOf({ answer: { skills: [fired], gap: complete }, failure: null, tileCount: 1, view: 'cost' })).toBeNull();
  });

  it('shows the tiles that have landed while the rest of the answer arrives', () => {
    expect(mapPanelOf({ answer: { skills: [fired], gap: null }, failure: null, tileCount: 1, view: 'cost' })).toBeNull();
  });

  it('says No signal when the store cannot be read, even with never-fired skills listed at zero', () => {
    const gap: Gap = { kind: 'unreachable', missing: 'Studio could not read the events store.' };

    const panel = mapPanelOf({ answer: { skills: [neverFired], gap }, failure: null, tileCount: 0, view: 'activations' });

    expect([panel?.word, panel?.tone]).toEqual(['No signal', 'failed']);
  });

  it('keeps the tiles of the days that landed when the store stops part way', () => {
    const gap: Gap = { kind: 'unreachable', missing: 'Studio could not read the events store.' };

    expect(mapPanelOf({ answer: { skills: [fired], gap }, failure: null, tileCount: 1, view: 'cost' })).toBeNull();
  });

  it('says No link when the API itself did not answer', () => {
    const panel = mapPanelOf({ answer: null, failure: 'GET /api/skills returned 502', tileCount: 0, view: 'cost' });

    expect([panel?.word, panel?.tone]).toEqual(['No link', 'failed']);
  });

  it('says Arriving while the first answer is on its way', () => {
    const panel = mapPanelOf({ answer: null, failure: null, tileCount: 0, view: 'cost' });

    expect([panel?.word, panel?.busy]).toEqual(['Arriving', true]);
  });

  it('says Arriving, not No Cost, while no landed day has given a tile', () => {
    const panel = mapPanelOf({ answer: { skills: [neverFired], gap: null }, failure: null, tileCount: 0, view: 'cost' });

    expect([panel?.word, panel?.busy]).toEqual(['Arriving', true]);
  });

  it('names the Gap when no skill is listed at all', () => {
    const gap: Gap = { kind: 'quiet', missing: 'Telemetry is on and the events store holds nothing for this period.' };

    expect(wordOf(mapPanelOf({ answer: { skills: [], gap }, failure: null, tileCount: 0, view: 'cost' }))).toBe('Quiet');
  });

  it('says Nothing when no skill is listed and nothing is missing', () => {
    expect(wordOf(mapPanelOf({ answer: { skills: [], gap: complete }, failure: null, tileCount: 0, view: 'cost' }))).toBe(
      'Nothing',
    );
  });

  it('says what the listed skills lack when none of them can be sized in the chosen view', () => {
    const answer = { skills: [neverFired], gap: complete };

    expect(wordOf(mapPanelOf({ answer, failure: null, tileCount: 0, view: 'cost' }))).toBe('No Cost');
    expect(wordOf(mapPanelOf({ answer, failure: null, tileCount: 0, view: 'activations' }))).toBe('No Activations');
  });
});
