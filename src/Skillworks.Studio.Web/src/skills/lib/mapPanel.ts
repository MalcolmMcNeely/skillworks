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

const arriving: MapPanel = { glyph: '◌', word: 'Arriving', tone: 'hud', busy: true };

export function mapPanelOf(state: {
  answer: Pick<SkillsAnswer, 'skills' | 'gap'> | null;
  failure: string | null;
  tileCount: number;
  view: MapView;
}): MapPanel | null {
  const { answer, failure, tileCount, view } = state;

  if (answer === null) {
    return failure === null ? arriving : { glyph: '✕', word: noLink, tone: 'failed', busy: false };
  }

  // Ahead of the zero checks: never-fired skills are still listed, and No Cost would read as a quiet week.
  if (answer.gap?.kind === 'unreachable') {
    return { glyph: '✕', word: signalOf(answer.gap.kind).word, tone: 'failed', busy: false };
  }

  if (tileCount > 0) {
    return null;
  }

  // The catalogue's zeros land before any day, and a day still to come may give them a tile.
  if (answer.gap === null) {
    return arriving;
  }

  if (answer.skills.length === 0) {
    return { glyph: '—', word: answer.gap.kind === 'complete' ? 'Nothing' : signalOf(answer.gap.kind).word, tone: 'dim', busy: false };
  }

  return { glyph: '0', word: `No ${viewWords[view]}`, tone: 'dim', busy: false };
}
