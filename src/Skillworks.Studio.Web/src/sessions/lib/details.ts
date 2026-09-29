import { describeMoney, describeTokens } from '../../shared/figures/lib/figures';

export type Purpose = 'work' | 'subagent' | 'side';

export type SideRequest =
  | 'awaySummary'
  | 'promptSuggestion'
  | 'sessionTitle'
  | 'compaction'
  | 'subagentSummary'
  | 'webPageRead'
  | 'webSearch'
  | 'other';

export interface TurnDetails {
  purpose: Purpose;
  side: SideRequest | null;
  // Claude Code's own value, so a Side request Studio has no name for still says what it was.
  sentAs: string | null;
  outputTokens: number;
  cost: number;
}

export interface DetailsPage {
  kind: 'details';
  turns: Record<string, TurnDetails>;
}

const purposeWords: Record<Exclude<Purpose, 'side'>, string> = {
  work: 'Work on the Prompt',
  subagent: "Subagent's work",
};

const sideWords: Record<Exclude<SideRequest, 'other'>, string> = {
  awaySummary: 'Recap while you were away',
  promptSuggestion: 'Next-prompt suggestion',
  sessionTitle: 'Session title',
  compaction: 'Compaction',
  subagentSummary: 'Subagent summary',
  webPageRead: 'Web page read',
  webSearch: 'Web search',
};

export function describePurpose(turn: TurnDetails): string {
  if (turn.purpose !== 'side') {
    return purposeWords[turn.purpose];
  }

  if (turn.side === null || turn.side === 'other') {
    return turn.sentAs === null ? 'Side request' : `Side request: ${turn.sentAs}`;
  }

  return sideWords[turn.side];
}

// Null details are a line not yet arrived, so a row keeps the words its Step carries until then.
export function rowLineOf(step: { id: string; kind: string; words: string | null }, turns: Record<string, TurnDetails> | null): string | null {
  const turn = step.kind === 'turn' ? turns?.[step.id] : undefined;

  if (turn === undefined) {
    return step.words;
  }

  return `${describePurpose(turn)} · ${describeTokens(turn.outputTokens)} output tokens · ${describeMoney(turn.cost)}`;
}
