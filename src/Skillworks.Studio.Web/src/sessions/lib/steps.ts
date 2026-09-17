import type { Gap, StoresEnd } from '../../gaps/lib/gaps';
import type { AgentsPage, Depth } from './agents';
import type { ContextPage, ContextPoint } from './context';
import type { Exchange, ExchangesPage } from './conversation';
import type { Session } from './sessions';
import type { SkillCall, SkillCallsPage } from './skillCalls';

export type StepKind = 'prompt' | 'turn' | 'answer' | 'tool' | 'refused' | 'fault';

export interface Step {
  id: string;
  kind: StepKind;
  // Claude Code writes its event once the Step is over, so the API works this start back from the length.
  atUtc: string;
  lengthMs: number;
  tool: string | null;
  fault: boolean;
  words: string | null;
}

export interface SessionHead {
  kind: 'head';
  // Null where the store holds no run under that id, which a mistyped address gives.
  session: Session | null;
}

export interface StepsPage {
  kind: 'steps';
  steps: Step[];
}

export type SessionLine =
  | SessionHead
  | StepsPage
  | ExchangesPage
  | SkillCallsPage
  | ContextPage
  | AgentsPage
  | StoresEnd;

export interface SessionAnswer {
  session: Session | null;
  steps: Step[];
  exchanges: Exchange[];
  skillCalls: SkillCall[];
  context: ContextPoint[];
  limitTokens: number | null;
  // Thin until the spans land, which is the second part of one read and not a second read.
  depth: Depth;
  agents: Record<string, string>;
  // No steps yet is not the same as a run with none, so the timeline waits for this rather than for the answer to end.
  landed: boolean;
  arriving: boolean;
  events: Gap | null;
  traces: Gap | null;
}

export function foldSessionLine(answer: SessionAnswer | null, line: SessionLine): SessionAnswer {
  if (line.kind === 'head') {
    return {
      session: line.session,
      steps: [],
      exchanges: [],
      skillCalls: [],
      context: [],
      limitTokens: null,
      depth: 'thin',
      agents: {},
      landed: false,
      arriving: true,
      events: null,
      traces: null,
    };
  }

  if (answer === null) {
    throw new Error(`A session answer starts with its head, not a ${line.kind} line.`);
  }

  if (line.kind === 'end') {
    return { ...answer, arriving: false, events: line.events, traces: line.traces };
  }

  if (line.kind === 'exchanges') {
    return { ...answer, exchanges: line.exchanges };
  }

  if (line.kind === 'skillCalls') {
    return { ...answer, skillCalls: line.skillCalls };
  }

  if (line.kind === 'context') {
    return { ...answer, context: line.points, limitTokens: line.limitTokens };
  }

  if (line.kind === 'agents') {
    return { ...answer, depth: line.depth, agents: line.agents };
  }

  return { ...answer, steps: line.steps, landed: true };
}

export interface Mark {
  step: Step;
  startMs: number;
  endMs: number;
}

export function marksOf(steps: readonly Step[]): Mark[] {
  return steps.map((step) => {
    const startMs = Date.parse(step.atUtc);

    return { step, startMs, endMs: startMs + step.lengthMs };
  });
}

export type Range = [number, number];

// Null where nothing ran, as a run with no Step has no stretch to draw.
export function runSpan(marks: readonly Mark[]): Range | null {
  if (marks.length === 0) {
    return null;
  }

  return marks.reduce<Range>(
    (span, mark) => [Math.min(span[0], mark.startMs), Math.max(span[1], mark.endMs)],
    [marks[0].startMs, marks[0].endMs],
  );
}

export const stretchesOf = (marks: readonly Mark[]): [number, number][] => marks.map((mark) => [mark.startMs, mark.endMs]);

export type Lane = 'prompt' | 'model' | 'shell' | 'edit' | 'read' | 'tool' | 'fault';

export const lanes: readonly { key: Lane; label: string }[] = [
  { key: 'prompt', label: 'Prompts' },
  { key: 'model', label: 'Model' },
  { key: 'shell', label: 'Shell' },
  { key: 'edit', label: 'Edit & write' },
  { key: 'read', label: 'Read & search' },
  { key: 'tool', label: 'Other tools' },
  { key: 'fault', label: 'Faults' },
];

// A tool nobody has named here belongs in Other tools, as Studio never guesses what a tool does.
const families: Record<string, Lane> = {
  Bash: 'shell',
  PowerShell: 'shell',
  Edit: 'edit',
  Write: 'edit',
  NotebookEdit: 'edit',
  Read: 'read',
  Grep: 'read',
  Glob: 'read',
};

// A failed Step sits in its own lane and in Faults too, so the Faults lane alone answers what went wrong.
export function lanesOf(step: Step): Lane[] {
  if (step.kind === 'prompt') {
    return ['prompt'];
  }

  if (step.kind === 'turn' || step.kind === 'answer') {
    return ['model'];
  }

  if (step.kind === 'fault') {
    return ['fault'];
  }

  const lane = step.tool === null ? 'tool' : (families[step.tool] ?? 'tool');

  return step.fault ? [lane, 'fault'] : [lane];
}

export type Tone = 'model' | 'tool' | 'refused' | 'fault';

// What a mark is drawn as, in its own lane and in Faults alike, so a failed call reads failed where it happened.
export function toneOf(step: Step): Tone {
  if (step.fault) {
    return 'fault';
  }

  if (step.kind === 'refused') {
    return 'refused';
  }

  return step.kind === 'turn' || step.kind === 'answer' ? 'model' : 'tool';
}

const stepWords: Record<StepKind, string> = {
  prompt: 'Prompt',
  turn: 'Model',
  answer: 'Answer',
  tool: 'Tool call',
  refused: 'Tool call',
  fault: 'Model fault',
};

export function titleOf(step: Step): string {
  return step.tool ?? stepWords[step.kind];
}

export function noteOf(step: Step): string | null {
  if (step.kind === 'refused') {
    return 'Refused';
  }

  return step.kind === 'tool' && step.fault ? 'Failed' : null;
}

const second = 1_000;

const minute = 60 * second;

const hour = 60 * minute;

// A Step can be four milliseconds or forty minutes, so the unit follows the figure.
export function describeSpell(lengthMs: number): string {
  if (lengthMs < second) {
    return `${Math.round(lengthMs)} ms`;
  }

  if (lengthMs < minute) {
    return `${(lengthMs / second).toFixed(lengthMs < 10 * second ? 1 : 0)} s`;
  }

  if (lengthMs < hour) {
    return `${Math.floor(lengthMs / minute)}m ${twoFigures(Math.floor((lengthMs % minute) / second))}s`;
  }

  return `${Math.floor(lengthMs / hour)}h ${twoFigures(Math.floor((lengthMs % hour) / minute))}m`;
}

// UTC, as the Filter counts whole UTC days and a local clock would move a late Step to the wrong day.
export function describeClock(atMs: number, seconds = false): string {
  return new Date(atMs).toISOString().slice(11, seconds ? 19 : 16);
}

function twoFigures(value: number): string {
  return String(value).padStart(2, '0');
}
