import { describe, expect, it } from 'vitest';
import { explainsEmpty } from './gaps';

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
