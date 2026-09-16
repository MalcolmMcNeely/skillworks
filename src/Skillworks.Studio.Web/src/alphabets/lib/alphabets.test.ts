import { describe, expect, it } from 'vitest';
import { lampSymbols } from '../../health/lib/health';
import { pageSymbols } from '../../pages/lib/pages';
import { triggerSymbols } from '../../provenance/lib/triggers';
import { sortSymbols } from '../../sessions/lib/sessions';
import { mapNoticeSymbols } from '../../skills/lib/mapNotice';
import { readoutSymbols } from '../../skills/lib/readout';
import { missingSymbols } from '../../skills/lib/skills';
import { sliceSymbols } from '../../skills/lib/strip';
import { switchSymbols } from '../../telemetry/lib/telemetry';
import { crossings, type SymbolTable } from './alphabets';

// Listed by hand, so a new table joins this list or the rule does not reach it.
const tables: Record<string, SymbolTable> = {
  pages: pageSymbols,
  lamps: lampSymbols,
  mapNotice: mapNoticeSymbols,
  missing: missingSymbols,
  readout: readoutSymbols,
  slices: sliceSymbols,
  sorts: sortSymbols,
  telemetrySwitch: switchSymbols,
  triggers: triggerSymbols,
};

describe('the symbols on screen', () => {
  it('gives every symbol one alphabet, so a reader never learns the same shape twice', () => {
    expect(crossings(tables)).toEqual([]);
  });

  it('lets one symbol mean broken wherever something is broken', () => {
    for (const name of ['lamps', 'mapNotice', 'slices', 'telemetrySwitch']) {
      expect(tables[name]?.glyphs).toContain('✕');
    }
  });
});

describe('crossings', () => {
  it('reports a symbol two alphabets claim, and names both tables', () => {
    expect(
      crossings({
        pages: { alphabet: 'identity', glyphs: ['●'] },
        lamps: { alphabet: 'condition', glyphs: ['●'] },
      }),
    ).toEqual([{ glyph: '●', tables: ['pages', 'lamps'] }]);
  });

  it('leaves a symbol reused inside one alphabet alone', () => {
    expect(
      crossings({
        lamps: { alphabet: 'condition', glyphs: ['✕'] },
        slices: { alphabet: 'condition', glyphs: ['✕'] },
      }),
    ).toEqual([]);
  });

  it('reports every crossing, so one run names them all', () => {
    expect(
      crossings({
        pages: { alphabet: 'identity', glyphs: ['●', '◈'] },
        lamps: { alphabet: 'condition', glyphs: ['●'] },
        triggers: { alphabet: 'cause', glyphs: ['◈'] },
      }).map((crossing) => crossing.glyph),
    ).toEqual(['●', '◈']);
  });
});
