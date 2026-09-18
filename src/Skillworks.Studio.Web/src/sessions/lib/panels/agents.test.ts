import { describe, expect, it } from 'vitest';
import {
  agentSpellsOf,
  briefNote,
  depthTone,
  describeDepth,
  mainAgent,
  noSubagentsWord,
  ranBy,
  ranByOne,
  tallyOf,
  type Subagent,
} from './agents';

function subagent(id: string, held: Partial<Subagent> = {}): Subagent {
  return {
    id,
    name: 'Find the leak',
    type: 'Explore',
    atUtc: '2026-09-14T09:00:11.000Z',
    lengthMs: 28_000,
    toolCalls: 3,
    cost: 0.4,
    faults: 1,
    brief: 'Read every file under src and',
    report: 'The handle is left open in Blob.',
    ...held,
  };
}

describe('ranBy', () => {
  it('reads not known where no span landed, so a missing span is never read as the main agent', () => {
    expect(ranBy(false, { '4': 'agent-a' }, '4')).toBe('Not known');
  });

  it('names the agent whose span carried the step', () => {
    expect(ranBy(true, { '4': 'agent-a' }, '4')).toBe('agent-a');
  });

  it('puts a step no agent id named on the main agent, as only a subagent carries one', () => {
    expect(ranBy(true, {}, '4')).toBe(mainAgent);
  });
});

describe('describeDepth', () => {
  it('says how much of a run can be read, in a word', () => {
    expect(describeDepth('thin')).toBe('Thin');
    expect(describeDepth('full')).toBe('Full');
  });
});

describe('depthTone', () => {
  it('reads quiet while a run is still thin, as an answer still arriving has fallen short of nothing', () => {
    expect(depthTone('thin', null)).toBe('quiet');
    expect(depthTone('thin', { kind: 'quiet', missing: 'Nothing was traced.' })).toBe('quiet');
  });

  it('reads failed only where the trace store itself fell short', () => {
    expect(depthTone('thin', { kind: 'unreachable', missing: 'The trace store could not be read.' })).toBe('failed');
  });

  it('reads live once the spans have landed', () => {
    expect(depthTone('full', { kind: 'complete', missing: null })).toBe('live');
  });
});

describe('agentSpellsOf', () => {
  it('gives a subagent the bounds a View and a panel both read it by', () => {
    expect(agentSpellsOf([subagent('agent-a')])).toEqual([
      { agent: subagent('agent-a'), startMs: Date.parse('2026-09-14T09:00:11.000Z'), endMs: Date.parse('2026-09-14T09:00:39.000Z') },
    ]);
  });
});

describe('tallyOf', () => {
  it('adds up what the subagents cost and did', () => {
    const tally = tallyOf(agentSpellsOf([subagent('agent-a'), subagent('agent-b', { cost: 1.6, toolCalls: 1, faults: 0 })]));

    expect(tally).toEqual({ subagents: 2, toolCalls: 4, cost: 2, faults: 1 });
  });
});

describe('briefNote', () => {
  it('says the rest of a brief was never recorded, so a reader never reads it as the whole of it', () => {
    expect(briefNote(subagent('agent-a'))).toBe('The rest of the brief was not recorded.');
  });

  it('says a brief was not recorded rather than showing nothing at all', () => {
    expect(briefNote(subagent('agent-a', { brief: null }))).toBe('The brief was not recorded.');
  });
});

describe('noSubagentsWord', () => {
  it('says a run with no span cannot know, as no span means no subagent can be found', () => {
    expect(noSubagentsWord(false, 0)).toBe('A run with no spans cannot say which subagents it ran.');
  });

  it('tells a run that ran none from a View that holds none', () => {
    expect(noSubagentsWord(true, 0)).toBe('No subagent ran in this run.');
    expect(noSubagentsWord(true, 2)).toBe('No subagent ran in view.');
  });
});

describe('ranByOne', () => {
  const marks = [{ step: { id: '1' } }, { step: { id: '2' } }, { step: { id: '3' } }];
  const agents = { '1': 'agent-a', '2': 'agent-b' };

  it('keeps every step while no subagent is open', () => {
    expect(ranByOne(marks, agents, null)).toEqual(marks);
  });

  it('keeps only what the open subagent ran, so its tool calls are never the main agent', () => {
    expect(ranByOne(marks, agents, 'agent-a')).toEqual([{ step: { id: '1' } }]);
  });
});
