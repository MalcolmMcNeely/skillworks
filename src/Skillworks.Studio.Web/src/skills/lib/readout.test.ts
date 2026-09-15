import { describe, expect, it } from 'vitest';
import type { PlacedTile } from './map';
import { describeAgo, readoutAt, readoutRows, readoutSize } from './readout';
import type { SkillSummary, TurnTotals } from './skills';

const spent: TurnTotals = { cost: 1, inputTokens: 100, outputTokens: 200, cacheReadTokens: 300, cacheCreationTokens: 400 };

const now = Date.parse('2026-09-15T12:00:00Z');

function skill(more: Partial<SkillSummary> = {}): SkillSummary {
  return {
    name: 'grilling',
    activations: 4,
    triggers: [],
    repositories: [],
    models: [],
    efforts: [],
    spend: spent,
    origins: [],
    each: 0.25,
    lastFired: '2026-09-15T09:00:00Z',
    spark: [],
    ...more,
  };
}

function valueOf(rows: readonly { label: string; value: string }[], label: string): string | undefined {
  return rows.find((row) => row.label === label)?.value;
}

describe('readoutRows', () => {
  it('reads out the figures a tile has no room to print', () => {
    const rows = readoutRows(
      skill({
        models: ['claude-opus-5[1m]', 'claude-sonnet-5'],
        efforts: ['high'],
        repositories: ['acme/nu', 'acme/xi'],
      }),
      now,
    );

    expect(rows.map((row) => [row.label, row.value])).toEqual([
      ['Cost', '$1.00'],
      ['Activations', '4'],
      ['Each', '$0.25'],
      ['Tokens', '1K'],
      ['Model', 'claude-opus-5[1m], claude-sonnet-5'],
      ['Effort', 'high'],
      ['Last', '3h'],
      ['Via', 'None'],
      ['Repositories', 'acme/nu, acme/xi'],
    ]);
  });

  it('says a skill whose Turns went unnamed spent nothing that Studio can read', () => {
    const rows = readoutRows(skill({ spend: null, models: null, efforts: null, each: null }), now);

    expect([valueOf(rows, 'Cost'), valueOf(rows, 'Tokens'), valueOf(rows, 'Model'), valueOf(rows, 'Effort')]).toEqual([
      'Not named',
      'Not named',
      'Not named',
      'Not named',
    ]);
  });

  it('says a skill that spent but never fired has no Each, rather than an unnamed one', () => {
    const rows = readoutRows(skill({ activations: 0, each: null, lastFired: null }), now);

    expect([valueOf(rows, 'Each'), valueOf(rows, 'Last')]).toEqual(['None', 'None']);
  });

  it('writes Via as a glyph and a count per trigger, most first', () => {
    const rows = readoutRows(
      skill({
        triggers: [
          { trigger: 'claude-proactive', activations: 1 },
          { trigger: 'user-slash', activations: 3 },
        ],
      }),
      now,
    );

    expect(rows.find((row) => row.label === 'Via')).toEqual({
      label: 'Via',
      value: '/3 ✦1',
      reading: 'Typed 3. Claude chose it 1',
    });
  });

  it('leaves every row but Via without a reading, as words are already what they hold', () => {
    const rows = readoutRows(skill(), now);

    expect(rows.filter((row) => row.reading !== null)).toEqual([]);
  });
});

describe('describeAgo', () => {
  it('counts whole hours up to two days, then whole days', () => {
    const readings = [
      '2026-09-15T11:00:00Z',
      '2026-09-14T13:00:00Z',
      '2026-09-13T12:00:00Z',
      '2026-09-01T12:00:00Z',
    ].map((instant) => describeAgo(instant, now));

    expect(readings).toEqual(['1h', '23h', '2d', '14d']);
  });

  it('says this hour for a firing in the hour that is still running', () => {
    expect(describeAgo('2026-09-15T12:00:00Z', now)).toBe('This hour');
  });
});

describe('readoutAt', () => {
  const map = { width: 800, height: 600 };

  function tile(x: number, y: number, width = 100, height = 100): PlacedTile {
    return { tile: { kind: 'unnamed', key: 'unnamed', rank: 1, value: 1, spend: spent }, x, y, width, height };
  }

  it('puts the readout to the right of the tile', () => {
    expect(readoutAt(tile(20, 40), map)).toEqual({ left: 128, top: 40 });
  });

  it('puts it to the left when the right would run off the map', () => {
    expect(readoutAt(tile(600, 40), map)).toEqual({ left: 356, top: 40 });
  });

  it('keeps it whole on the map when neither side has room', () => {
    const narrow = { width: 300, height: 600 };

    expect(readoutAt(tile(0, 40, 300), narrow)).toEqual({ left: 32, top: 40 });
  });

  it('lifts it clear of the bottom edge', () => {
    expect(readoutAt(tile(20, 560), map)).toEqual({ left: 128, top: 364 });
  });

  it('holds it on a map too small for it, rather than pushing it off the top left', () => {
    expect(readoutAt(tile(0, 0, 100, 100), { width: 100, height: 100 })).toEqual({ left: 0, top: 0 });
  });

  it('is sized for every row it holds', () => {
    expect(readoutSize).toEqual({ width: 236, height: 236 });
  });
});
