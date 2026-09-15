import { signalOf } from '../../gaps/lib/gaps';
import { noLink } from '../../http/lib/errors';
import { viewWords, type MapView } from './map';
import type { SkillsAnswer } from './skills';

export interface MapPanel {
  glyph: string;
  word: string;
  tone: 'failed' | 'hud' | 'dim';
  busy: boolean;
}

export function mapPanelOf(state: {
  answer: Pick<SkillsAnswer, 'skills' | 'gap'> | null;
  failure: string | null;
  tileCount: number;
  view: MapView;
}): MapPanel | null {
  const { answer, failure, tileCount, view } = state;

  if (answer === null) {
    return failure === null
      ? { glyph: '◌', word: 'Arriving', tone: 'hud', busy: true }
      : { glyph: '✕', word: noLink, tone: 'failed', busy: false };
  }

  // Ahead of the zero checks: never-fired skills are still listed, and No Cost would read as a quiet week.
  if (answer.gap.kind === 'unreachable') {
    return { glyph: '✕', word: signalOf(answer.gap.kind).word, tone: 'failed', busy: false };
  }

  if (tileCount > 0) {
    return null;
  }

  if (answer.skills.length === 0) {
    return { glyph: '—', word: answer.gap.kind === 'complete' ? 'Nothing' : signalOf(answer.gap.kind).word, tone: 'dim', busy: false };
  }

  return { glyph: '0', word: `No ${viewWords[view]}`, tone: 'dim', busy: false };
}
