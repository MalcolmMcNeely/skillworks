import { describeCount, describeMoney, describeTokens } from '../../shared/figures/lib/figures';
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
  // Both null where no Span landed for the Turn, as no event carries them.
  stopReason: string | null;
  attempt: number | null;
}

export interface ToolDetails {
  tool: string | null;
  passed: boolean;
  error: string | null;
  // Input and parameters are Claude Code's own JSON, and null where it kept them back.
  input: string | null;
  inputBytes: number | null;
  parameters: string | null;
  command: string | null;
  description: string | null;
  resultBytes: number | null;
  allowedBy: string | null;
}

export type TokenPart = 'cacheRead' | 'cacheWrite' | 'input' | 'output';

export type TimePart = 'wait' | 'writing';

export interface DetailsPage {
  kind: 'details';
  turns: Record<string, TurnDetails>;
  tools: Record<string, ToolDetails>;
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

const stopWords: Record<string, string> = {
  end_turn: 'Finished its reply',
  tool_use: 'Asked for a tool',
  max_tokens: 'Cut off at the output limit',
  refusal: 'Refused',
};

export function describeStop(turn: TurnDetails): string {
  if (turn.stopReason === null) {
    return notKnown;
  }

  return Object.hasOwn(stopWords, turn.stopReason) ? stopWords[turn.stopReason] : turn.stopReason;
}

export function describeAttempt(turn: TurnDetails): string {
  return turn.attempt === null ? notKnown : `Attempt ${turn.attempt}`;
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

const allowedWords: Record<string, string> = {
  config: 'Allowed by your settings',
  user_temporary: 'You allowed it, this once',
  user_permanent: 'You allowed it, from now on',
  hook: 'A hook allowed it',
};

export function describeAllowedBy(call: ToolDetails): string {
  if (call.allowedBy === null) {
    return notKnown;
  }

  return Object.hasOwn(allowedWords, call.allowedBy) ? allowedWords[call.allowedBy] : call.allowedBy;
}

export function describeOutcome(call: ToolDetails): string {
  return call.passed ? 'Passed' : 'Failed';
}

export function describeWithheld(call: ToolDetails): string {
  return call.inputBytes === null ? 'Withheld' : `Withheld · ${describeCount(call.inputBytes)} bytes`;
}

// Claude Code cuts each value of the input at 512 characters and the whole near 4K, so the JSON may not close.
function fieldsOf(json: string | null): Record<string, unknown> | null {
  if (json === null) {
    return null;
  }

  try {
    const read: unknown = JSON.parse(json);

    return typeof read === 'object' && read !== null ? (read as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function textOf(fields: Record<string, unknown> | null, field: string): string | null {
  const value = fields?.[field];

  return typeof value === 'string' && value !== '' ? value : null;
}

export function fileOf(call: ToolDetails): string | null {
  const input = fieldsOf(call.input);

  return textOf(input, 'file_path') ?? textOf(input, 'notebook_path');
}

const inputOpening = 80;

function acted(call: ToolDetails): string | null {
  const input = fieldsOf(call.input);

  switch (call.tool) {
    case 'Bash':
      return call.description ?? call.command;
    case 'Edit':
    case 'MultiEdit':
    case 'Write':
    case 'NotebookEdit':
    case 'Read':
      return fileOf(call);
    case 'Skill':
      return textOf(input, 'skill') ?? textOf(fieldsOf(call.parameters), 'skill_name');
    case 'Grep':
    case 'Glob':
      return textOf(input, 'pattern');
    case 'Agent':
    case 'Task':
      return textOf(input, 'description');
    default:
      if (call.input === null) {
        return null;
      }

      return call.input.length > inputOpening ? `${call.input.slice(0, inputOpening)}…` : call.input;
  }
}

export function whatItDid(call: ToolDetails): string {
  const did = acted(call) ?? (call.input === null ? describeWithheld(call) : (call.tool ?? notKnown));

  return call.passed ? did : `Failed · ${did}`;
}

// Null details are a line not yet arrived, so a row keeps the words its Step carries until then.
export function rowLineOf(
  step: { id: string; kind: string; words: string | null },
  turns: Record<string, TurnDetails> | null,
  tools: Record<string, ToolDetails> | null,
): string | null {
  const call = step.kind === 'tool' ? tools?.[step.id] : undefined;

  if (call !== undefined) {
    return whatItDid(call);
  }

  const turn = step.kind === 'turn' ? turns?.[step.id] : undefined;

  if (turn === undefined) {
    return step.words;
  }

  return `${describePurpose(turn)} · ${describeTokens(turn.outputTokens)} output tokens · ${describeMoney(turn.cost)}`;
}
