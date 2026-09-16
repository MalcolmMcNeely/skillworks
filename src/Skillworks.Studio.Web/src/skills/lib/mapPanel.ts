import type { SymbolTable } from '../../alphabets/lib/alphabets';
import { signalOf } from '../../gaps/lib/gaps';
import { noLink } from '../../http/lib/errors';
import type { SkillsAnswer } from './answer';
import { viewWords, type MapView } from './map';

export interface MapPanel {
  glyph: string;
  word: string;
  tone: 'failed' | 'hud' | 'dim';
  busy: boolean;
}

// A glyph apiece, so the panel says why the map is bare without its word being read.
const panelGlyphs = {
  arriving: '◌',
  failed: '✕',
  nothing: '—',
  noFigure: '0',
} as const;

export const mapPanelSymbols: SymbolTable = { alphabet: 'condition', glyphs: Object.values(panelGlyphs) };

const arriving: MapPanel = { glyph: panelGlyphs.arriving, word: 'Arriving', tone: 'hud', busy: true };

export function mapPanelOf(state: {
  answer: Pick<SkillsAnswer, 'skills' | 'gap'> | null;
  failure: string | null;
  tileCount: number;
  view: MapView;
}): MapPanel | null {
  const { answer, failure, tileCount, view } = state;

  if (answer === null) {
    return failure === null ? arriving : { glyph: panelGlyphs.failed, word: noLink, tone: 'failed', busy: false };
  }

  if (tileCount > 0) {
    return null;
  }

  // Ahead of the zero checks: never-fired skills are still listed, and No Cost would read as a quiet week.
  if (answer.gap?.kind === 'unreachable') {
    return { glyph: panelGlyphs.failed, word: signalOf(answer.gap.kind).word, tone: 'failed', busy: false };
  }

  // The catalogue's zeros land before any day, and a day still to come may give them a tile.
  if (answer.gap === null) {
    return arriving;
  }

  if (answer.skills.length === 0) {
    return {
      glyph: panelGlyphs.nothing,
      word: answer.gap.kind === 'complete' ? 'Nothing' : signalOf(answer.gap.kind).word,
      tone: 'dim',
      busy: false,
    };
  }

  return { glyph: panelGlyphs.noFigure, word: `No ${viewWords[view]}`, tone: 'dim', busy: false };
}
