import { describe, expect, it } from 'vitest';
import type { Subagent } from '../timeline/agents';
import type { Exchange, SubagentCost } from '../timeline/conversation';
import { beforeFirstPromptWord, costBreakdownOf, shareOf, type CostBar } from './costBreakdown';

const exchange = (index: number, cost: number, subagents: SubagentCost[] | null = []): Exchange => ({
  index,
  atUtc: new Date(index * 60_000).toISOString(),
  lengthMs: 30_000,
  prompt: `Prompt ${index}`,
  promptLength: 8,
  answer: null,
  answerLength: 0,
  turns: 1,
  toolCalls: 0,
  cost,
  subagents,
});

const subagent = (id: string, name: string): Subagent => ({
  id,
  name,
  type: null,
  atUtc: new Date(0).toISOString(),
  lengthMs: 0,
  toolCalls: 0,
  cost: 0,
  faults: 0,
  brief: null,
  report: null,
});

// Every piece drawn on every bar, so a Subagent drawn on top of its Exchange would show up as Cost counted twice.
const drawnCost = (bars: readonly CostBar[]) =>
  bars.reduce((total, bar) => total + bar.ownCost + bar.subagents.reduce((sum, spent) => sum + spent.cost, 0), 0);

describe('costBreakdownOf', () => {
  it('draws one bar for each Exchange and one for the Turns before the first Prompt', () => {
    const breakdown = costBreakdownOf([exchange(0, 0.5), exchange(1, 0.25)], 0.125, []);

    expect(breakdown?.bars.map((bar) => bar.word)).toEqual(['Exchange 1', 'Exchange 2', beforeFirstPromptWord]);
    expect(breakdown?.bars.map((bar) => bar.cost)).toEqual([0.5, 0.25, 0.125]);
  });

  it('adds the bars up to the Session’s Cost', () => {
    const breakdown = costBreakdownOf(
      [exchange(0, 0.5, [{ agent: 'agent-a', cost: 0.25 }]), exchange(1, 0.25)],
      0.125,
      [subagent('agent-a', 'Find the tests')],
    );

    expect(breakdown?.total).toBe(0.875);
    expect(drawnCost(breakdown?.bars ?? [])).toBe(0.875);
  });

  it('sets a Subagent’s part apart inside its Exchange’s Cost and never adds it on top', () => {
    const breakdown = costBreakdownOf(
      [exchange(0, 1, [{ agent: 'agent-a', cost: 0.5 }, { agent: 'agent-b', cost: 0.25 }])],
      0,
      [subagent('agent-a', 'Find the tests'), subagent('agent-b', 'Read the docs')],
    );
    const [bar] = breakdown?.bars ?? [];

    expect(bar.cost).toBe(1);
    expect(bar.ownCost).toBe(0.25);
    expect(bar.subagents).toEqual([
      { agent: 'agent-a', name: 'Find the tests', cost: 0.5 },
      { agent: 'agent-b', name: 'Read the docs', cost: 0.25 },
    ]);
    expect(drawnCost([bar])).toBe(1);
  });

  it('names a Subagent the run said nothing about by its id', () => {
    const breakdown = costBreakdownOf([exchange(0, 1, [{ agent: 'agent-z', cost: 0.5 }])], 0, []);

    expect(breakdown?.bars[0].subagents[0].name).toBe('agent-z');
  });

  it('reads the Subagent parts as not known where no Span named the agent behind a Turn', () => {
    const breakdown = costBreakdownOf([exchange(0, 1, null)], 0, []);

    expect(breakdown?.subagentsKnown).toBe(false);
    expect(breakdown?.bars[0].ownCost).toBe(1);
    expect(breakdown?.bars[0].subagents).toEqual([]);
  });

  it('reads the Subagent parts as known once every Exchange has them', () => {
    expect(costBreakdownOf([exchange(0, 1), exchange(1, 1)], 0, [])?.subagentsKnown).toBe(true);
  });

  it('keeps the row for the Turns before the first Prompt when they cost nothing', () => {
    const breakdown = costBreakdownOf([exchange(0, 1)], 0, []);

    expect(breakdown?.bars.at(-1)).toMatchObject({ exchange: null, word: beforeFirstPromptWord, cost: 0 });
  });

  it('has no bar to draw for a run with no Exchange', () => {
    expect(costBreakdownOf([], 0.5, [])).toBeNull();
  });

  it('draws each bar against the dearest one', () => {
    const breakdown = costBreakdownOf([exchange(0, 1), exchange(1, 0.5)], 0, []);

    expect(breakdown?.bars.map((bar) => shareOf(bar.cost, breakdown))).toEqual([1, 0.5, 0]);
  });

  it('draws nothing past the edge in a run that cost nothing', () => {
    const breakdown = costBreakdownOf([exchange(0, 0)], 0, []);

    expect(breakdown === null ? null : shareOf(0, breakdown)).toBe(0);
  });
});
