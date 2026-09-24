import { describe, expect, it } from 'vitest';
import { lampsOf, type Part } from './health';

const marketplace: Part = {
  name: 'Marketplace',
  state: 'working',
  detail: 'Reading skills from /home/me/skillworks/plugins.',
  action: null,
};

const store: Part = {
  name: 'Events store',
  state: 'broken',
  detail: 'http://localhost:3100/ could not be read (connection refused).',
  action: 'Start Studio’s containers with aspire run.',
};

const traces: Part = {
  name: 'Trace store',
  state: 'working',
  detail: 'http://localhost:3200/ answered.',
  action: null,
};

describe('lampsOf', () => {
  it('shows a working part as a lamp with a glyph and a call sign, and opens nothing from it', () => {
    expect(lampsOf({ parts: [marketplace] }, null)).toEqual([
      { callSign: 'Marketplace', state: 'working', glyph: '●', word: 'Working', opens: null },
    ]);
  });

  it('opens the detail and the action from the lamp of a broken part', () => {
    expect(lampsOf({ parts: [store] }, null)).toEqual([
      {
        callSign: 'Events store',
        state: 'broken',
        glyph: '✕',
        word: 'Broken',
        opens: {
          detail: 'http://localhost:3100/ could not be read (connection refused).',
          action: 'Start Studio’s containers with aspire run.',
        },
      },
    ]);
  });

  it('opens the detail and the action from the lamp of a part that is off', () => {
    // Off is not a fault, but it still has an action for the developer to take.
    const [lamp] = lampsOf({ parts: [{ ...store, state: 'off' }] }, null);

    expect(lamp?.opens).toEqual({ detail: store.detail, action: store.action });
  });

  it('opens nothing from the lamp of a part that is still starting', () => {
    const [lamp] = lampsOf({ parts: [{ ...store, state: 'starting' }] }, null);

    expect(lamp?.opens).toBeNull();
  });

  it('gives each state a glyph of its own, so colour is never the only signal', () => {
    const glyphs = (['working', 'starting', 'off', 'broken'] as const).map(
      (state) => lampsOf({ parts: [{ ...marketplace, state }] }, null)[0]?.glyph,
    );

    expect(new Set(glyphs).size).toBe(4);
  });

  it('leaves telemetry to the switch beside the lamps, so the one fact has one control', () => {
    const telemetry: Part = {
      name: 'Claude Code telemetry',
      state: 'off',
      detail: 'Claude Code is not emitting telemetry.',
      action: 'Turn telemetry on with the Telemetry switch.',
    };

    expect(lampsOf({ parts: [store, telemetry, marketplace] }, null).map((lamp) => lamp.callSign)).toEqual([
      'Events store',
      'Marketplace',
    ]);
  });

  it('tells the two stores apart, so a broken one names itself', () => {
    expect(lampsOf({ parts: [store, traces] }, null).map((lamp) => [lamp.callSign, lamp.state])).toEqual([
      ['Events store', 'broken'],
      ['Trace store', 'working'],
    ]);
  });

  it('keeps the name of the part it lights', () => {
    const [lamp] = lampsOf({ parts: [{ ...marketplace, name: 'Collector' }] }, null);

    expect(lamp?.callSign).toBe('Collector');
  });

  it('shows one API lamp, starting, while the API has not answered', () => {
    expect(lampsOf(null, null)).toEqual([
      { callSign: 'API', state: 'starting', glyph: '◌', word: 'Starting', opens: null },
    ]);
  });

  it('shows one broken API lamp that opens the failure when the API could not be read', () => {
    expect(lampsOf(null, 'GET /api/health returned 502')).toEqual([
      {
        callSign: 'API',
        state: 'broken',
        glyph: '✕',
        word: 'Broken',
        opens: { detail: 'GET /api/health returned 502', action: 'Start Studio with aspire run.' },
      },
    ]);
  });

  it('drops the parts of an earlier answer when checking again fails, as they may no longer hold', () => {
    const lamps = lampsOf({ parts: [marketplace] }, 'Failed to fetch');

    expect(lamps.map((lamp) => [lamp.callSign, lamp.state])).toEqual([['API', 'broken']]);
  });
});
