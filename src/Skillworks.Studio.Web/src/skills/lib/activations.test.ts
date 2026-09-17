import { describe, expect, it } from 'vitest';
import type { Gap } from '../../gaps/lib/gaps';
import { describeFiredAt, firedInNoRun, foldActivationsLine, noActivations, type Activation } from './activations';

const ended = (gap: Gap) => foldActivationsLine(noActivations, { kind: 'end', gap });

const activation: Activation = {
  skill: 'tdd',
  atUtc: '2026-09-14T09:00:00+00:00',
  session: '8f1c0a9e-0000-4000-8000-000000000001',
  repository: 'malcolmania/skillworks',
  trigger: 'user-slash',
};

describe('foldActivationsLine', () => {
  it('takes the activations and marks them landed', () => {
    const answer = foldActivationsLine(noActivations, { kind: 'activations', activations: [activation] });

    expect(answer.activations).toEqual([activation]);
    expect(answer.landed).toBe(true);
  });

  it('keeps the gap the answer ended with, so a store that fell short never reads as a skill that never fired', () => {
    const answer = foldActivationsLine(noActivations, {
      kind: 'end',
      gap: { kind: 'unreachable', missing: 'Studio could not read the events store.' },
    });

    expect(answer.gap?.kind).toBe('unreachable');
    expect(answer.landed).toBe(true);
  });

  it('keeps the activations that landed when the answer ends', () => {
    const landed = foldActivationsLine(noActivations, { kind: 'activations', activations: [activation] });
    const whole = foldActivationsLine(landed, { kind: 'end', gap: { kind: 'complete', missing: null } });

    expect(whole.activations).toEqual([activation]);
  });

  it('waits before saying a skill never fired, so an answer on its way does not read as none', () => {
    expect(noActivations.landed).toBe(false);
    expect(noActivations.activations).toEqual([]);
  });
});

describe('firedInNoRun', () => {
  it('says a skill fired in no run only when the answer is complete', () => {
    expect(firedInNoRun(ended({ kind: 'complete', missing: null }))).toBe(true);
  });

  it('refuses to call a store that could not be read a skill that never fired', () => {
    expect(firedInNoRun(ended({ kind: 'unreachable', missing: 'The store could not be read.' }))).toBe(false);
    expect(firedInNoRun(ended({ kind: 'telemetryOff', missing: 'Telemetry is off.' }))).toBe(false);
    expect(firedInNoRun(ended({ kind: 'quiet', missing: 'The store holds nothing.' }))).toBe(false);
  });

  it('says nothing while the answer is still on its way', () => {
    expect(firedInNoRun(noActivations)).toBe(false);
  });

  it('says nothing when the skill did fire', () => {
    const landed = foldActivationsLine(noActivations, { kind: 'activations', activations: [activation] });

    expect(firedInNoRun(foldActivationsLine(landed, { kind: 'end', gap: { kind: 'complete', missing: null } }))).toBe(false);
  });
});

describe('describeFiredAt', () => {
  it('reads an activation to the minute', () => {
    expect(describeFiredAt('2026-09-14T09:00:00+00:00')).toBe('2026-09-14 09:00');
  });

  it('turns an instant sent at another offset into UTC, so it lists under the day the filter counts', () => {
    expect(describeFiredAt('2026-09-15T01:30:00+03:00')).toBe('2026-09-14 22:30');
  });
});
