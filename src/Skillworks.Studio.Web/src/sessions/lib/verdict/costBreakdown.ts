import type { Subagent } from '../timeline/agents';
import type { Exchange } from '../timeline/conversation';

export interface NamedSubagentCost {
  agent: string;
  name: string;
  cost: number;
}

export interface CostBar {
  exchange: Exchange | null;
  word: string;
  cost: number;
  // What is left once the Subagents' costs are taken out, so the pieces of a bar add up to its Cost and no further.
  ownCost: number;
  subagents: NamedSubagentCost[];
}

export interface CostBreakdown {
  bars: CostBar[];
  total: number;
  largest: number;
  // False where no Span named the agent behind each Turn, so a Subagent's cost could not be set apart.
  subagentsKnown: boolean;
}

export const beforeFirstPromptWord = 'Before the first Prompt';

export const noExchangeWord = 'Nobody typed a Prompt in this run, so it has no Exchange to break its Cost down by.';

export function costBreakdownOf(
  exchanges: readonly Exchange[],
  beforeFirstPrompt: number,
  subagents: readonly Subagent[],
): CostBreakdown | null {
  if (exchanges.length === 0) {
    return null;
  }

  const names = new Map(subagents.map((subagent) => [subagent.id, subagent.name]));

  const bars: CostBar[] = [
    ...exchanges.map((exchange) => {
      const named = (exchange.subagents ?? []).map((spent) => ({ ...spent, name: names.get(spent.agent) ?? spent.agent }));

      return {
        exchange,
        word: `Exchange ${exchange.index + 1}`,
        cost: exchange.cost,
        ownCost: named.reduce((own, spent) => own - spent.cost, exchange.cost),
        subagents: named,
      };
    }),
    { exchange: null, word: beforeFirstPromptWord, cost: beforeFirstPrompt, ownCost: beforeFirstPrompt, subagents: [] },
  ];

  return {
    bars,
    total: bars.reduce((total, bar) => total + bar.cost, 0),
    largest: Math.max(...bars.map((bar) => bar.cost)),
    subagentsKnown: exchanges.every((exchange) => exchange.subagents !== null),
  };
}

export function shareOf(cost: number, breakdown: CostBreakdown): number {
  return breakdown.largest > 0 ? cost / breakdown.largest : 0;
}
