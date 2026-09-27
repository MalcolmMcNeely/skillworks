import { describe, expect, it } from 'vitest';
import { readView } from './view';
import { describeLit, litBy, readHighlight, toggled, withHighlight, type Highlight } from './highlight';
import { marksOf, type Step } from '../steps';

function step(id: string, fields: Partial<Step> = {}): Step {
  return {
    id,
    kind: 'tool',
    atUtc: '2026-09-14T09:00:00.000Z',
    lengthMs: 0,
    tool: 'Bash',
    fault: false,
    words: null,
    skill: null,
    unnamed: false,
    skillKnown: true,
    cost: 0,
    ...fields,
  };
}

const turn = { kind: 'turn', tool: null } as const;

const bash: Highlight = { kind: 'tool', name: 'Bash' };

describe('readHighlight', () => {
  it('reads a tool from the address', () => {
    expect(readHighlight(new URLSearchParams('lit=tool:Bash'))).toEqual(bash);
  });

  it('keeps a colon inside a tool name', () => {
    expect(readHighlight(new URLSearchParams('lit=tool:mcp:search'))).toEqual({ kind: 'tool', name: 'mcp:search' });
  });

  it('reads a skill from the address', () => {
    expect(readHighlight(new URLSearchParams('lit=skill:tdd'))).toEqual({ kind: 'skill', name: 'tdd' });
  });

  it('reads No skill and Unnamed spend apart from a skill of either name', () => {
    expect(readHighlight(new URLSearchParams('lit=no-skill'))).toEqual({ kind: 'noSkill' });
    expect(readHighlight(new URLSearchParams('lit=unnamed'))).toEqual({ kind: 'unnamed' });
    expect(readHighlight(new URLSearchParams('lit=skill:unnamed'))).toEqual({ kind: 'skill', name: 'unnamed' });
  });

  it('reads no Highlight from an address without one', () => {
    expect(readHighlight(new URLSearchParams(''))).toBeNull();
  });

  it('reads no Highlight from a hand-typed address it cannot make sense of', () => {
    expect(readHighlight(new URLSearchParams('lit=Bash'))).toBeNull();
    expect(readHighlight(new URLSearchParams('lit=tool:'))).toBeNull();
    expect(readHighlight(new URLSearchParams('lit=skill:'))).toBeNull();
  });
});

describe('withHighlight', () => {
  it('writes a tool that reads back the same', () => {
    const written = withHighlight(new URLSearchParams(''), { kind: 'tool', name: 'mcp__docs__read' });

    expect(written.get('lit')).toBe('tool:mcp__docs__read');
    expect(readHighlight(written)).toEqual({ kind: 'tool', name: 'mcp__docs__read' });
  });

  it('writes every skill row that reads back the same', () => {
    const rows: Highlight[] = [{ kind: 'skill', name: 'diagnosing-bugs' }, { kind: 'noSkill' }, { kind: 'unnamed' }];

    expect(rows.map((row) => withHighlight(new URLSearchParams(''), row).get('lit'))).toEqual([
      'skill:diagnosing-bugs',
      'no-skill',
      'unnamed',
    ]);
    expect(rows.map((row) => readHighlight(withHighlight(new URLSearchParams(''), row)))).toEqual(rows);
  });

  it('takes the Highlight out of the address when it is cleared', () => {
    expect(withHighlight(new URLSearchParams('lit=tool:Bash'), null).has('lit')).toBe(false);
  });

  it('leaves the View and the opened Step where they were', () => {
    const params = new URLSearchParams('at=1000&until=5000&step=7');
    const written = withHighlight(params, bash);

    expect(readView(written)).toEqual([1000, 5000]);
    expect(written.get('step')).toBe('7');
  });
});

describe('describeLit', () => {
  it('says what is lit for a tool, a skill, No skill and Unnamed spend', () => {
    expect(describeLit(bash)).toBe('every Bash call');
    expect(describeLit({ kind: 'skill', name: 'tdd' })).toBe('every Step of tdd');
    expect(describeLit({ kind: 'noSkill' })).toBe('every Step of No skill');
    expect(describeLit({ kind: 'unnamed' })).toBe('every Step of Unnamed spend');
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

  it('tells a skill from a tool of the same name', () => {
    expect(toggled(bash, { kind: 'skill', name: 'Bash' })).toEqual({ kind: 'skill', name: 'Bash' });
  });

  it('puts out No skill when it is picked again', () => {
    expect(toggled({ kind: 'noSkill' }, { kind: 'noSkill' })).toBeNull();
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

  it('lights the Turns attributed to a skill and the Tool calls they asked for', () => {
    const marks = marksOf([
      step('1', { ...turn, skill: 'tdd' }),
      step('2', { skill: 'tdd' }),
      step('3', { kind: 'refused', skill: 'tdd' }),
      step('4', { ...turn, skill: 'implement' }),
      step('5', { kind: 'prompt', tool: null, skill: 'tdd' }),
    ]);

    expect([...litBy({ kind: 'skill', name: 'tdd' }, marks)].toSorted()).toEqual(['1', '2', '3']);
  });

  it('lights only its own Steps for a skill that called another inside its spell', () => {
    const marks = marksOf([
      step('1', { ...turn, skill: 'implement' }),
      step('2', { ...turn, skill: 'tdd' }),
      step('3', { skill: 'tdd' }),
      step('4', { ...turn, skill: 'implement' }),
    ]);

    expect([...litBy({ kind: 'skill', name: 'implement' }, marks)].toSorted()).toEqual(['1', '4']);
  });

  it('lights only the Turns of a skill in a Session with no Spans, as no Tool call there has a known skill', () => {
    const marks = marksOf([
      step('1', { ...turn, skill: 'tdd' }),
      step('2', { skillKnown: false }),
      step('3', { kind: 'refused', skillKnown: false }),
      step('4', { ...turn }),
    ]);

    expect([...litBy({ kind: 'skill', name: 'tdd' }, marks)]).toEqual(['1']);
    expect([...litBy({ kind: 'noSkill' }, marks)]).toEqual(['4']);
    expect([...litBy({ kind: 'unnamed' }, marks)]).toEqual([]);
  });

  it('still lights every call of a tool in a Session with no Spans', () => {
    const marks = marksOf([step('1', { skillKnown: false }), step('2', { kind: 'refused', skillKnown: false })]);

    expect([...litBy(bash, marks)].toSorted()).toEqual(['1', '2']);
  });

  it('lights No skill and Unnamed spend apart', () => {
    const marks = marksOf([step('1', turn), step('2'), step('3', { ...turn, unnamed: true }), step('4', { unnamed: true })]);

    expect([...litBy({ kind: 'noSkill' }, marks)].toSorted()).toEqual(['1', '2']);
    expect([...litBy({ kind: 'unnamed' }, marks)].toSorted()).toEqual(['3', '4']);
  });
});
