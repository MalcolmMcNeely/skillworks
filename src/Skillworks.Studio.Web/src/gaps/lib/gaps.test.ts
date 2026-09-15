import { describe, expect, it } from 'vitest';
import { explainsEmpty, signalOf } from './gaps';

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

describe('explainsEmpty', () => {
  it('lets a Gap under which nothing arrived explain an empty screen on its own', () => {
    expect(explainsEmpty('unreachable')).toBe(true);
    expect(explainsEmpty('quiet')).toBe(true);
    expect(explainsEmpty('telemetryUnknown')).toBe(true);
  });

  it('leaves an empty screen to the filter when telemetry is off only on this machine', () => {
    // The store can still hold other machines' events, so the filter may be why nothing matched.
    expect(explainsEmpty('telemetryOff')).toBe(false);
  });

  it('leaves an empty screen to the filter when nothing is missing', () => {
    expect(explainsEmpty('complete')).toBe(false);
  });
});
