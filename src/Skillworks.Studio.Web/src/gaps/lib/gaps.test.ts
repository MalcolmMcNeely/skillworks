import { describe, expect, it } from 'vitest';
import { signalOf } from './gaps';

describe('signalOf', () => {
  it('says Live when nothing is missing', () => {
    expect(signalOf('complete')).toEqual({ word: 'Live', tone: 'live' });
  });

  it('says No signal when the store could not be read, so an outage never reads as a quiet week', () => {
    expect(signalOf('unreachable')).toEqual({ word: 'No signal', tone: 'failed' });
  });

  it('says Cut short when the store held more than it answered with, so half an answer never reads as the whole', () => {
    expect(signalOf('shortened')).toEqual({ word: 'Cut short', tone: 'warned' });
  });

  it('says Quiet when the store was read and held nothing', () => {
    expect(signalOf('quiet')).toEqual({ word: 'Quiet', tone: 'quiet' });
  });

  it('names telemetry, as a warning, when the switch is why nothing arrived', () => {
    expect(signalOf('telemetryOff')).toEqual({ word: 'Telemetry off', tone: 'warned' });
    expect(signalOf('telemetryUnknown')).toEqual({ word: 'Telemetry unknown', tone: 'warned' });
  });

  it('names withheld words apart from telemetry, as the two ask for different lines in different files', () => {
    expect(signalOf('wordsOff')).toEqual({ word: 'Words withheld', tone: 'warned' });
  });
});
