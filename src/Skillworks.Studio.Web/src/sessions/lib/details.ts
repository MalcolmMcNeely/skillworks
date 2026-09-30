import { describeCount, describeLength, describeMoney, describeTokens } from '../../shared/figures/lib/figures';
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
  // False where no Span landed for the call, so its output, wait and running time are not known rather than empty.
  traced: boolean;
  output: string | null;
  diff: string | null;
  waitedMs: number | null;
  ranMs: number | null;
  // Read from events and not Spans, so null means no hook ran rather than not known.
  hooksBefore: HookRun | null;
  hooksAfter: HookRun | null;
}

export interface HookRun {
  count: number;
  lengthMs: number;
}

export type ToolTimePart = 'hooksBefore' | 'waiting' | 'running' | 'hooksAfter';

export type TokenPart = 'cacheRead' | 'cacheWrite' | 'input' | 'output';

export type TimePart = 'wait' | 'writing';

// The same fields a Tool call asks with, so a refused call reads what it wanted to do by the same rule.
export interface RefusalDetails {
  tool: string | null;
  input: string | null;
  inputBytes: number | null;
  parameters: string | null;
  command: string | null;
  description: string | null;
  refusedBy: string | null;
}

export interface FaultDetails {
  error: string | null;
  statusCode: number | null;
  attempt: number | null;
  model: string | null;
  effort: string | null;
  purpose: Purpose;
  side: SideRequest | null;
  sentAs: string | null;
}

export interface StepDetails {
  turns: Record<string, TurnDetails>;
  tools: Record<string, ToolDetails>;
  refusals: Record<string, RefusalDetails>;
  faults: Record<string, FaultDetails>;
}

export interface DetailsPage extends StepDetails {
  kind: 'details';
}

export type AskedWith = Pick<ToolDetails, 'tool' | 'input' | 'inputBytes' | 'parameters' | 'command' | 'description'>;

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

export function describePurpose(turn: Pick<TurnDetails, 'purpose' | 'side' | 'sentAs'>): string {
  if (turn.purpose !== 'side') {
    return purposeWords[turn.purpose];
  }

  if (turn.side === null || turn.side === 'other') {
    return turn.sentAs === null ? 'Side request' : `Side request: ${turn.sentAs}`;
  }

  return sideWords[turn.side];
}

// A Fault carries no speed, so it reads as the normal one.
export function describeModel(turn: Pick<TurnDetails, 'model' | 'effort'> & { speed?: string | null }): string {
  if (turn.model === null) {
    return notKnown;
  }

  const effort = turn.effort === null ? '' : ` · ${turn.effort} effort`;
  const speed = turn.speed === undefined || turn.speed === null || turn.speed === 'normal' ? '' : ` · ${turn.speed}`;

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

export function describeAttempt(turn: { attempt: number | null }): string {
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

const refusedWords: Record<string, string> = {
  config: 'Refused by your settings',
  hook: 'A hook refused it',
  user_reject: 'You refused it',
  user_abort: 'You stopped it',
};

export function describeRefusedBy(refusal: RefusalDetails): string {
  if (refusal.refusedBy === null) {
    return notKnown;
  }

  return Object.hasOwn(refusedWords, refusal.refusedBy) ? refusedWords[refusal.refusedBy] : refusal.refusedBy;
}

export function describeStatusCode(fault: FaultDetails): string {
  return fault.statusCode === null ? notKnown : String(fault.statusCode);
}

export function describeOutcome(call: ToolDetails): string {
  return call.passed ? 'Passed' : 'Failed';
}

function withheldOf(bytes: number | null): string {
  return bytes === null ? 'Withheld' : `Withheld · ${describeCount(bytes)} bytes`;
}

export function describeWithheld(call: Pick<AskedWith, 'inputBytes'>): string {
  return withheldOf(call.inputBytes);
}

export function outputOf(call: ToolDetails): string | null {
  return call.diff ?? call.output;
}

// Claude Code sends no more than this of an output, and Studio adds no cap of its own.
const sentOfOutput = 2_048;

// Claude Code never sends the output of a Subagent call, so its absence says nothing was kept back.
const unsentOutput = new Set(['Agent', 'Task']);

export function describeOutputNote(call: ToolDetails): string | null {
  const shown = outputOf(call);

  if (!call.traced || (shown === null && call.tool !== null && unsentOutput.has(call.tool))) {
    return notKnown;
  }

  if (shown === null) {
    return withheldOf(call.resultBytes);
  }

  if (shown.length >= sentOfOutput && call.resultBytes !== null && call.resultBytes > shown.length) {
    return `The first ${describeCount(sentOfOutput)} characters of ${describeCount(call.resultBytes)} bytes`;
  }

  return null;
}

function hookPartOf(part: ToolTimePart, word: string, run: HookRun | null) {
  if (run === null) {
    return { part, word, ms: 0, figure: 'No hooks' };
  }

  return {
    part,
    word,
    ms: run.lengthMs,
    figure: `${describeLength(run.lengthMs)} · ${run.count} ${run.count === 1 ? 'hook' : 'hooks'}`,
  };
}

function spanPartOf(part: ToolTimePart, word: string, ms: number | null) {
  return { part, word, ms, figure: ms === null ? notKnown : describeLength(ms) };
}

export function toolTimePartsOf(call: ToolDetails): { part: ToolTimePart; word: string; ms: number | null; figure: string }[] {
  return [
    hookPartOf('hooksBefore', 'Hooks before', call.hooksBefore),
    spanPartOf('waiting', 'Waiting for approval', call.traced ? (call.waitedMs ?? 0) : null),
    spanPartOf('running', 'Running', call.traced ? call.ranMs : null),
    hookPartOf('hooksAfter', 'Hooks after', call.hooksAfter),
  ];
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

export function fileOf(call: Pick<AskedWith, 'input'>): string | null {
  const input = fieldsOf(call.input);

  return textOf(input, 'file_path') ?? textOf(input, 'notebook_path');
}

const inputOpening = 80;

function acted(call: AskedWith): string | null {
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

function whatItAsked(call: AskedWith): string {
  return acted(call) ?? (call.input === null ? describeWithheld(call) : (call.tool ?? notKnown));
}

export function whatItDid(call: ToolDetails): string {
  const did = whatItAsked(call);

  return call.passed ? did : `Failed · ${did}`;
}

// Null details are a line not yet arrived, so a row keeps the words its Step carries until then.
export function rowLineOf(step: { id: string; kind: string; words: string | null }, details: StepDetails | null): string | null {
  const call = step.kind === 'tool' ? details?.tools[step.id] : undefined;

  if (call !== undefined) {
    return whatItDid(call);
  }

  const refusal = step.kind === 'refused' ? details?.refusals[step.id] : undefined;

  if (refusal !== undefined) {
    return whatItAsked(refusal);
  }

  const fault = step.kind === 'fault' ? details?.faults[step.id] : undefined;

  if (fault !== undefined) {
    return fault.error ?? notKnown;
  }

  const turn = step.kind === 'turn' ? details?.turns[step.id] : undefined;

  if (turn === undefined) {
    return step.words;
  }

  return `${describePurpose(turn)} · ${describeTokens(turn.outputTokens)} output tokens · ${describeMoney(turn.cost)}`;
}
