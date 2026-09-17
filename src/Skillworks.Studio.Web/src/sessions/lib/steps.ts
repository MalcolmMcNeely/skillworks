import type { Gap, StoresEnd } from '../../gaps/lib/gaps';
import type { Range } from './view';
import type { FindingsPage } from './findings';
import type { Activation, ActivationsPage } from './panels/activations';
import type { AgentsPage, Depth, Subagent } from './panels/agents';
import type { ContextPage, ContextPoint } from './panels/context';
import type { Exchange, ExchangesPage } from './panels/conversation';
import type { SplitPage } from './panels/split';
import type { TracePage } from './panels/trace';
import type { Session } from './sessions';

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
  | ActivationsPage
  | ContextPage
  | AgentsPage
  | TracePage
  | SplitPage
  | FindingsPage
  | StoresEnd;

export interface SessionAnswer {
  session: Session | null;
  steps: Step[];
  exchanges: Exchange[];
  activations: Activation[];
  context: ContextPoint[];
  limitTokens: number | null;
  // Thin until the spans land, which is the second part of one read and not a second read.
  depth: Depth;
  agents: Record<string, string>;
  subagents: Subagent[];
  // Only the Spans say what ran inside what, so a Thin run nests nothing.
  inside: Record<string, string>;
  // Null until the spans land, as an empty split and a split nobody has read yet mean different things.
  split: SplitPage | null;
  // Null until the spans land, as a run that crossed no bar and one nobody has read yet mean different things.
  findings: FindingsPage | null;
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
      activations: [],
      context: [],
      limitTokens: null,
      depth: 'thin',
      agents: {},
      subagents: [],
      inside: {},
      split: null,
      findings: null,
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

  if (line.kind === 'activations') {
    return { ...answer, activations: line.activations };
  }

  if (line.kind === 'context') {
    return { ...answer, context: line.points, limitTokens: line.limitTokens };
  }

  if (line.kind === 'agents') {
    return { ...answer, depth: line.depth, agents: line.agents, subagents: line.subagents };
  }

  if (line.kind === 'trace') {
    return { ...answer, inside: line.inside };
  }

  if (line.kind === 'split') {
    return { ...answer, split: line };
  }

  if (line.kind === 'findings') {
    return { ...answer, findings: line };
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

// Null where nothing ran, as a run with no Step has no bounds to draw.
export function runSpan(marks: readonly Mark[]): Range | null {
  if (marks.length === 0) {
    return null;
  }

  return marks.reduce<Range>(
    (span, mark) => [Math.min(span[0], mark.startMs), Math.max(span[1], mark.endMs)],
    [marks[0].startMs, marks[0].endMs],
  );
}

export const boundsOf = (marks: readonly Mark[]): [number, number][] => marks.map((mark) => [mark.startMs, mark.endMs]);

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

// UTC, as the Filter counts whole UTC days and a local clock would move a late Step to the wrong day.
export function describeClock(atMs: number, seconds = false): string {
  return new Date(atMs).toISOString().slice(11, seconds ? 19 : 16);
}
