import { describeMoney, describeTokens } from '../../shared/figures/lib/figures';
import { notKnown } from './sessions';

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
  model: string | null;
  effort: string | null;
  speed: string | null;
  cost: number;
  lengthMs: number;
  // Null where Claude Code gave no wait, as nought would read as an instant start.
  firstWordMs: number | null;
  cacheReadTokens: number;
  cacheWriteTokens: number;
  inputTokens: number;
  outputTokens: number;
  words: string | null;
  wordsLength: number | null;
}

export type TokenPart = 'cacheRead' | 'cacheWrite' | 'input' | 'output';

export type TimePart = 'wait' | 'writing';

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

export function describeModel(turn: TurnDetails): string {
  if (turn.model === null) {
    return notKnown;
  }

  const effort = turn.effort === null ? '' : ` · ${turn.effort} effort`;
  const speed = turn.speed === null || turn.speed === 'normal' ? '' : ` · ${turn.speed}`;

  return `${turn.model}${effort}${speed}`;
}

export function tokenPartsOf(turn: TurnDetails): { part: TokenPart; word: string; tokens: number }[] {
  return [
    { part: 'cacheRead', word: 'Read from cache', tokens: turn.cacheReadTokens },
    { part: 'cacheWrite', word: 'Written to cache', tokens: turn.cacheWriteTokens },
    { part: 'input', word: 'New input', tokens: turn.inputTokens },
    { part: 'output', word: 'Output', tokens: turn.outputTokens },
  ];
}

// With no wait known, the writing is not known either, as the whole length would read as all writing.
export function timePartsOf(turn: TurnDetails): { part: TimePart; word: string; ms: number | null }[] {
  const wait = turn.firstWordMs;

  return [
    { part: 'wait', word: 'Wait for the first word', ms: wait },
    { part: 'writing', word: 'Writing', ms: wait === null ? null : Math.max(0, turn.lengthMs - wait) },
  ];
}

// Null details are a line not yet arrived, so a row keeps the words its Step carries until then.
export function rowLineOf(step: { id: string; kind: string; words: string | null }, turns: Record<string, TurnDetails> | null): string | null {
  const turn = step.kind === 'turn' ? turns?.[step.id] : undefined;

  if (turn === undefined) {
    return step.words;
  }

  return `${describePurpose(turn)} · ${describeTokens(turn.outputTokens)} output tokens · ${describeMoney(turn.cost)}`;
}
