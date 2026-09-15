import { describe, expect, it } from 'vitest';
import {
  describeDeliveries,
  describeDelivery,
  describeTrigger,
  describeTriggers,
  type Origin,
} from './provenance';

const local: Origin = {
  trigger: 'claude-proactive',
  source: 'projectSettings',
  plugin: null,
  marketplace: null,
};

const shipped: Origin = {
  trigger: 'user-slash',
  source: 'plugin',
  plugin: 'probekit',
  marketplace: 'privateprobe',
};

describe('describeTrigger', () => {
  it('tells the model choosing a skill from a developer typing it', () => {
    expect(describeTrigger('claude-proactive')).toBe('Claude chose it');
    expect(describeTrigger('user-slash')).toBe('A developer typed it');
  });

  it('shows a trigger it does not know as it arrived', () => {
    expect(describeTrigger('some-new-trigger')).toBe('some-new-trigger');
  });

  it('says nothing was recorded rather than leaving the cell empty', () => {
    expect(describeTrigger(null)).toBe('Not recorded');
  });
});

describe('describeDelivery', () => {
  it('names the plugin and the marketplace behind a shipped skill', () => {
    expect(describeDelivery(shipped)).toBe('probekit from privateprobe');
  });

  it('falls back to where a skill with no plugin was loaded from', () => {
    expect(describeDelivery(local)).toBe('projectSettings');
  });

  it('says nothing was recorded when the store named neither', () => {
    expect(describeDelivery({ trigger: null, source: null, plugin: null, marketplace: null })).toBe(
      'Not recorded',
    );
  });
});

describe('describeDeliveries', () => {
  it('keeps two ways of delivering one name apart', () => {
    expect(describeDeliveries([shipped, { ...shipped, marketplace: 'skillworks' }])).toBe(
      'probekit from privateprobe, probekit from skillworks',
    );
  });

  it('says the same thing once however many firings said it', () => {
    expect(describeDeliveries([local, local])).toBe('projectSettings');
  });

  it('says nothing was recorded when the store knew of no firing at all', () => {
    expect(describeDeliveries([])).toBe('Not recorded');
    expect(describeTriggers([])).toBe('Not recorded');
  });
});
