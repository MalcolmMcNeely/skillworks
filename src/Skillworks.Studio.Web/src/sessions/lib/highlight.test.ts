import { describe, expect, it } from 'vitest';
import { readRange } from './view';
import { litBy, readHighlight, toggled, withHighlight, type Highlight } from './highlight';
import { marksOf, type Step } from './steps';

function step(id: string, fields: Partial<Step> = {}): Step {
  return { id, kind: 'tool', atUtc: '2026-09-14T09:00:00.000Z', lengthMs: 0, tool: 'Bash', fault: false, words: null, ...fields };
}

const bash: Highlight = { kind: 'tool', name: 'Bash' };

describe('readHighlight', () => {
  it('reads a tool from the address', () => {
    expect(readHighlight(new URLSearchParams('lit=tool:Bash'))).toEqual(bash);
  });

  it('keeps a colon inside a tool name', () => {
    expect(readHighlight(new URLSearchParams('lit=tool:mcp:search'))).toEqual({ kind: 'tool', name: 'mcp:search' });
  });

  it('reads no Highlight from an address without one', () => {
    expect(readHighlight(new URLSearchParams(''))).toBeNull();
  });

  it('reads no Highlight from a hand-typed address it cannot make sense of', () => {
    expect(readHighlight(new URLSearchParams('lit=Bash'))).toBeNull();
    expect(readHighlight(new URLSearchParams('lit=tool:'))).toBeNull();
  });
});

describe('withHighlight', () => {
  it('writes a tool that reads back the same', () => {
    const written = withHighlight(new URLSearchParams(''), { kind: 'tool', name: 'mcp__docs__read' });

    expect(written.get('lit')).toBe('tool:mcp__docs__read');
    expect(readHighlight(written)).toEqual({ kind: 'tool', name: 'mcp__docs__read' });
  });

  it('takes the Highlight out of the address when it is cleared', () => {
    expect(withHighlight(new URLSearchParams('lit=tool:Bash'), null).has('lit')).toBe(false);
  });

  it('leaves the View and the opened Step where they were', () => {
    const params = new URLSearchParams('at=1000&until=5000&step=7');
    const written = withHighlight(params, bash);

    expect(readRange(written)).toEqual([1000, 5000]);
    expect(written.get('step')).toBe('7');
  });
});

describe('toggled', () => {
  it('lights a row nobody has lit', () => {
    expect(toggled(null, bash)).toEqual(bash);
  });

  it('puts out the lit row when it is picked again', () => {
    expect(toggled(bash, { kind: 'tool', name: 'Bash' })).toBeNull();
  });

  it('moves the light to another row', () => {
    expect(toggled(bash, { kind: 'tool', name: 'Read' })).toEqual({ kind: 'tool', name: 'Read' });
  });
});

describe('litBy', () => {
  it('lights every Tool call of the tool, refused ones and failed ones too', () => {
    const marks = marksOf([
      step('1'),
      step('2', { kind: 'refused' }),
      step('3', { fault: true }),
      step('4', { tool: 'Read' }),
      step('5', { kind: 'turn', tool: null }),
    ]);

    expect([...litBy(bash, marks)].toSorted()).toEqual(['1', '2', '3']);
  });

  it('lights nothing when the tool made no call', () => {
    expect(litBy({ kind: 'tool', name: 'Write' }, marksOf([step('1')])).size).toBe(0);
  });
});
