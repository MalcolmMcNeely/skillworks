import { describe, expect, it } from 'vitest';
import { signalOf } from './gaps';

describe('signalOf', () => {
  it('says Live when nothing is missing', () => {
    expect(signalOf('complete')).toEqual({ word: 'Live', tone: 'live' });
  });

  it('says No signal when the store could not be read, so an outage never reads as a quiet week', () => {
    expect(signalOf('unreachable')).toEqual({ word: 'No signal', tone: 'failed' });
  });

  it('says Quiet when the store was read and held nothing', () => {
    expect(signalOf('quiet')).toEqual({ word: 'Quiet', tone: 'quiet' });
  });

  it('names telemetry, as a warning, when the switch is why nothing arrived', () => {
    expect(signalOf('telemetryOff')).toEqual({ word: 'Telemetry off', tone: 'warned' });
    expect(signalOf('telemetryUnknown')).toEqual({ word: 'Telemetry unknown', tone: 'warned' });
  });
});
