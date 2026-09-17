import type { SymbolTable } from '../../alphabets/lib/alphabets';
import type { TriggerCount } from './provenance';

export interface TriggerMark {
  glyph: string;
  word: string;
  activations: number;
}

// A glyph apiece, so a tile too small for words still says whether Claude picked the skill up on its own.
const marks: Record<string, Omit<TriggerMark, 'activations'>> = {
  'claude-proactive': { glyph: '✦', word: 'Claude chose it' },
  'user-slash': { glyph: '/', word: 'Typed' },
  'nested-skill': { glyph: '↳', word: 'Called by a skill' },
  'agent-preload': { glyph: '◈', word: 'Given to an agent' },
};

const unrecorded: Omit<TriggerMark, 'activations'> = { glyph: '?', word: 'Not recorded' };

export const triggerSymbols: SymbolTable = {
  alphabet: 'cause',
  glyphs: [...Object.values(marks).map((mark) => mark.glyph), unrecorded.glyph],
};

// A trigger Claude Code adds later keeps its own name, so an Activation is never dropped or read as another trigger.
export function triggerMark(trigger: string | null): Omit<TriggerMark, 'activations'> {
  if (trigger === null) {
    return unrecorded;
  }

  return marks[trigger] ?? { glyph: unrecorded.glyph, word: trigger };
}

// A tile has room for three, so the busiest trigger must come first.
export function triggerMarks(counts: readonly TriggerCount[]): TriggerMark[] {
  return counts
    .filter((count) => count.activations > 0)
    .map((count) => ({ ...triggerMark(count.trigger), activations: count.activations }))
    .toSorted((a, b) => b.activations - a.activations);
}
