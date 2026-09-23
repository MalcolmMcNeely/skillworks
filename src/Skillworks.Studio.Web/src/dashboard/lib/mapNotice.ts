import type { SymbolTable } from '../../shared/alphabets/lib/alphabets';
import { signalOf } from '../../shared/gaps/lib/gaps';
import { noLink } from '../../shared/wire/lib/errors';
import type { SkillsAnswer } from './answer';
import { figureWords, type MapFigure } from './map';

export interface MapNotice {
  glyph: string;
  word: string;
  tone: 'failed' | 'hud' | 'dim';
  busy: boolean;
}

// A glyph apiece, so the notice says why the map is bare without its word being read.
const noticeGlyphs = {
  arriving: '◌',
  failed: '✕',
  // Never a dash: a dash means there is no answer at all, and this answer is complete and empty.
  nothing: '∅',
  noFigure: '0',
} as const;

export const mapNoticeSymbols: SymbolTable = { alphabet: 'condition', glyphs: Object.values(noticeGlyphs) };

const arriving: MapNotice = { glyph: noticeGlyphs.arriving, word: 'Arriving', tone: 'hud', busy: true };

export function mapNoticeOf(state: {
  answer: Pick<SkillsAnswer, 'skills' | 'gap'> | null;
  failure: string | null;
  tileCount: number;
  figure: MapFigure;
}): MapNotice | null {
  const { answer, failure, tileCount, figure } = state;

  if (answer === null) {
    return failure === null ? arriving : { glyph: noticeGlyphs.failed, word: noLink, tone: 'failed', busy: false };
  }

  if (tileCount > 0) {
    return null;
  }

  // Ahead of the zero checks: never-fired skills are still listed, and No Cost would read as a quiet week.
  if (answer.gap?.kind === 'unreachable') {
    return { glyph: noticeGlyphs.failed, word: signalOf(answer.gap.kind).word, tone: 'failed', busy: false };
  }

  // The catalogue's zeros land before any day, and a day still to come may give them a tile.
  if (answer.gap === null) {
    return arriving;
  }

  if (answer.skills.length === 0) {
    return {
      glyph: noticeGlyphs.nothing,
      word: answer.gap.kind === 'complete' ? 'Nothing' : signalOf(answer.gap.kind).word,
      tone: 'dim',
      busy: false,
    };
  }

  return { glyph: noticeGlyphs.noFigure, word: `No ${figureWords[figure]}`, tone: 'dim', busy: false };
}
