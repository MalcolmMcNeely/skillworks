import { describe, expect, it } from 'vitest';
import { depthTone, describeDepth, mainThread, ranBy } from './agents';

describe('ranBy', () => {
  it('reads not known in a thin run, so a missing span is never read as the main thread', () => {
    expect(ranBy('thin', { '4': 'agent-a' }, '4')).toBe('Not known');
  });

  it('names the agent whose span carried the step', () => {
    expect(ranBy('full', { '4': 'agent-a' }, '4')).toBe('agent-a');
  });

  it('puts a step no agent id named on the main thread, as only a subagent carries one', () => {
    expect(ranBy('full', {}, '4')).toBe(mainThread);
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
