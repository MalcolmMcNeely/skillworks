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
  // A part of the cost and never an addition to it. Null until a Span has named the agent behind each Turn.
  subagents: SubagentCost[] | null;
}

export interface SubagentCost {
  agent: string;
  cost: number;
}

export interface ExchangesPage {
  kind: 'exchanges';
  exchanges: Exchange[];
  // The Turns before the first Prompt sit in no Exchange, so without them the Exchanges fall short of the Session's Cost.
  beforeFirstPrompt: number;
}

// Worked out once, so the band on the timeline and the View it opens never disagree.
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
