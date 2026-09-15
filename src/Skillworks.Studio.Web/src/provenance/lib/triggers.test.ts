import { describe, expect, it } from 'vitest';
import { triggerMarks } from './triggers';

describe('triggerMarks', () => {
  it('gives each trigger Claude Code records its own glyph and word', () => {
    const marks = triggerMarks([
      { trigger: 'claude-proactive', activations: 4 },
      { trigger: 'user-slash', activations: 3 },
      { trigger: 'nested-skill', activations: 2 },
      { trigger: 'agent-preload', activations: 1 },
    ]);

    expect(marks).toEqual([
      { glyph: '✦', word: 'Claude chose it', activations: 4 },
      { glyph: '/', word: 'Typed', activations: 3 },
      { glyph: '↳', word: 'Called by a skill', activations: 2 },
      { glyph: '◈', word: 'Given to an agent', activations: 1 },
    ]);
  });

  it('puts the trigger with the most Activations first', () => {
    const marks = triggerMarks([
      { trigger: 'claude-proactive', activations: 1 },
      { trigger: 'user-slash', activations: 9 },
    ]);

    expect(marks.map((mark) => mark.glyph)).toEqual(['/', '✦']);
  });

  it('keeps the order the answer gave when two triggers tie', () => {
    const marks = triggerMarks([
      { trigger: 'agent-preload', activations: 2 },
      { trigger: 'user-slash', activations: 2 },
    ]);

    expect(marks.map((mark) => mark.glyph)).toEqual(['◈', '/']);
  });

  it('marks a firing recorded with no trigger as not recorded', () => {
    expect(triggerMarks([{ trigger: null, activations: 5 }])).toEqual([
      { glyph: '?', word: 'Not recorded', activations: 5 },
    ]);
  });

  it('keeps a trigger it does not know under its own name', () => {
    expect(triggerMarks([{ trigger: 'hook-fired', activations: 2 }])).toEqual([
      { glyph: '?', word: 'hook-fired', activations: 2 },
    ]);
  });

  it('leaves out a trigger nothing fired under', () => {
    expect(triggerMarks([{ trigger: 'user-slash', activations: 0 }])).toEqual([]);
  });
});
