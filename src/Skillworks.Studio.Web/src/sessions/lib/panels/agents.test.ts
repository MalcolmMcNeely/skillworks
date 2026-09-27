import { describe, expect, it } from 'vitest';
import { depthTone, describeDepth, mainAgent, ranBy, ranByOne } from './agents';

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
    expect(depthTone('thin', { kind: 'shortened', missing: 'The trace store cut its answer short.' })).toBe('failed');
  });

  it('reads live once the spans have landed', () => {
    expect(depthTone('full', { kind: 'complete', missing: null })).toBe('live');
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
