import { describe, expect, it } from 'vitest';
import {
  describeDeliveries,
  describeDelivery,
  describeMissingOrigin,
  describeProvenance,
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

describe('describeProvenance', () => {
  it('says what is missing in the words the API gave for it', () => {
    expect(
      describeProvenance({
        reachable: false,
        missing: 'Studio could not read the events store.',
        sinceUtc: '2026-09-05T00:00:00Z',
      }),
    ).toBe('Studio could not read the events store.');
  });

  it('says how far back the provenance on screen reaches when nothing is missing', () => {
    expect(
      describeProvenance({ reachable: true, missing: null, sinceUtc: '2026-09-05T00:00:00Z' }),
    ).toBe('Where a skill came from is known for events since 2026-09-05 00:00:00 UTC.');
  });
});

describe('describeMissingOrigin', () => {
  it('blames the store when the store is what failed', () => {
    expect(
      describeMissingOrigin({
        reachable: false,
        missing: 'Studio could not read the events store.',
        sinceUtc: '2026-09-05T00:00:00Z',
      }),
    ).toBe('Studio could not read the events store.');
  });

  it('says one firing has nothing recorded when the store answered for others', () => {
    // The store was read, and held events from that moment for other skills. Showing how far back
    // it reaches would answer a question about one firing with a fact about a month.
    expect(
      describeMissingOrigin({ reachable: true, missing: null, sinceUtc: '2026-09-05T00:00:00Z' }),
    ).toBe('The events store has nothing recorded for this firing.');
  });
});
