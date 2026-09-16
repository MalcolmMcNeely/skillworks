import { describeCount } from '../../figures/lib/figures';

export interface Exchange {
  index: number;
  atUtc: string;
  lengthMs: number;
  // Null where a switch withheld the words, which the length beside it still counts.
  prompt: string | null;
  promptLength: number;
  answer: string | null;
  answerLength: number;
  turns: number;
  toolCalls: number;
  cost: number;
}

export interface ExchangesPage {
  kind: 'exchanges';
  exchanges: Exchange[];
}

// Worked out once, so the band on the timeline and the block beneath it never disagree.
export interface Band {
  exchange: Exchange;
  startMs: number;
  endMs: number;
}

export function bandsOf(exchanges: readonly Exchange[]): Band[] {
  return exchanges.map((exchange) => {
    const startMs = Date.parse(exchange.atUtc);

    return { exchange, startMs, endMs: startMs + exchange.lengthMs };
  });
}

export interface Figures {
  exchanges: number;
  turns: number;
  toolCalls: number;
  cost: number;
}

export function figuresOf(bands: readonly Band[]): Figures {
  return bands.reduce<Figures>(
    (sum, { exchange }) => ({
      exchanges: sum.exchanges + 1,
      turns: sum.turns + exchange.turns,
      toolCalls: sum.toolCalls + exchange.toolCalls,
      cost: sum.cost + exchange.cost,
    }),
    { exchanges: 0, turns: 0, toolCalls: 0, cost: 0 },
  );
}

export function describeWithheld(length: number): string {
  return `Withheld · ${describeCount(length)} characters`;
}
