import { describe, expect, it } from 'vitest';
import type { Gap } from '../../gaps/lib/gaps';
import { mapNoticeOf } from './mapNotice';
import { missingWords, type SkillSummary } from './skills';

const noTokens = { inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, cacheCreationTokens: 0 };

const fired: SkillSummary = {
  name: 'grilling',
  activations: 3,
  triggers: [],
  repositories: [],
  models: [],
  efforts: [],
  spend: { ...noTokens, cost: 0.3 },
  each: 0.1,
  origins: [],
  lastFired: null,
  spark: [],
};

const neverFired: SkillSummary = { ...fired, name: 'tdd', activations: 0, each: null, spend: { ...noTokens, cost: 0 } };

const complete: Gap = { kind: 'complete', missing: null };

const unreachable: Gap = { kind: 'unreachable', missing: 'Studio could not read the events store.' };

describe('mapNoticeOf', () => {
  it('shows no notice once there are tiles to show', () => {
    expect(mapNoticeOf({ answer: { skills: [fired], gap: complete }, failure: null, tileCount: 1, view: 'cost' })).toBeNull();
  });

  it('shows the tiles that have landed while the rest of the answer arrives', () => {
    expect(mapNoticeOf({ answer: { skills: [fired], gap: null }, failure: null, tileCount: 1, view: 'cost' })).toBeNull();
  });

  it('says No signal when the store cannot be read, even with never-fired skills listed at zero', () => {
    const answer = { skills: [neverFired], gap: unreachable };

    const notice = mapNoticeOf({ answer, failure: null, tileCount: 0, view: 'activations' });

    expect([notice?.word, notice?.tone]).toEqual(['No signal', 'failed']);
  });

  it('keeps the tiles of the days that landed when the store stops part way', () => {
    const answer = { skills: [fired], gap: unreachable };

    expect(mapNoticeOf({ answer, failure: null, tileCount: 1, view: 'cost' })).toBeNull();
  });

  it('says No link when the API itself did not answer', () => {
    const notice = mapNoticeOf({ answer: null, failure: 'GET /api/skills returned 502', tileCount: 0, view: 'cost' });

    expect([notice?.word, notice?.tone]).toEqual(['No link', 'failed']);
  });

  it('says Arriving while the first answer is on its way', () => {
    const notice = mapNoticeOf({ answer: null, failure: null, tileCount: 0, view: 'cost' });

    expect([notice?.word, notice?.busy]).toEqual(['Arriving', true]);
  });

  it('says Arriving, not No Cost, while no landed day has given a tile', () => {
    const notice = mapNoticeOf({ answer: { skills: [neverFired], gap: null }, failure: null, tileCount: 0, view: 'cost' });

    expect([notice?.word, notice?.busy]).toEqual(['Arriving', true]);
  });

  it('names the Gap when no skill is listed at all', () => {
    const gap: Gap = { kind: 'quiet', missing: 'Telemetry is on and the events store holds nothing for this period.' };

    const notice = mapNoticeOf({ answer: { skills: [], gap }, failure: null, tileCount: 0, view: 'cost' });

    expect(notice?.word).toBe('Quiet');
  });

  it('says Nothing when no skill is listed and nothing is missing', () => {
    const notice = mapNoticeOf({ answer: { skills: [], gap: complete }, failure: null, tileCount: 0, view: 'cost' });

    expect(notice?.word).toBe('Nothing');
  });

  it('marks Nothing with the empty set, leaving the dash to mean there is no answer at all', () => {
    const notice = mapNoticeOf({ answer: { skills: [], gap: complete }, failure: null, tileCount: 0, view: 'cost' });

    expect(notice?.glyph).toBe('∅');
    expect(notice?.glyph).not.toBe(missingWords.noAnswer);
  });

  it('says what the listed skills lack when none of them can be sized in the chosen view', () => {
    const answer = { skills: [neverFired], gap: complete };

    expect(mapNoticeOf({ answer, failure: null, tileCount: 0, view: 'cost' })?.word).toBe('No Cost');
    expect(mapNoticeOf({ answer, failure: null, tileCount: 0, view: 'activations' })?.word).toBe('No Activations');
  });
});
