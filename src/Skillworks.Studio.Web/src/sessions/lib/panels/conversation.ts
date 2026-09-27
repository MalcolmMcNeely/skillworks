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
