import type { Gap, Signal } from '../../../gaps/lib/gaps';
import { notKnown } from '../sessions';

export type Depth = 'thin' | 'full';

export interface Subagent {
  id: string;
  name: string;
  type: string | null;
  atUtc: string;
  lengthMs: number;
  toolCalls: number;
  cost: number;
  faults: number;
  // Only the opening words of a brief were ever recorded, so this is the whole of what a reader can get.
  brief: string | null;
  report: string | null;
}

export interface AgentsPage {
  kind: 'agents';
  depth: Depth;
  // Only the Steps a Subagent ran, as the browser is sent a Session and never a Span.
  agents: Record<string, string>;
  subagents: Subagent[];
}

export const mainThread = 'Main thread';

// A Thin run has no Span to name the agent, so it reads not known rather than as the main thread's work.
export function ranBy(depth: Depth, agents: Record<string, string>, step: string): string {
  return depth === 'thin' ? notKnown : (agents[step] ?? mainThread);
}

export function describeDepth(depth: Depth): string {
  return depth === 'full' ? 'Full' : 'Thin';
}

// A run still arriving is Thin and not yet short of anything, so only a store that fell short reads failed.
export function depthTone(depth: Depth, gap: Gap | null): Signal['tone'] {
  if (depth === 'full') {
    return 'live';
  }

  return gap !== null && gap.kind === 'unreachable' ? 'failed' : 'quiet';
}

export interface Stint {
  agent: Subagent;
  startMs: number;
  endMs: number;
}

export function stintsOf(subagents: readonly Subagent[]): Stint[] {
  return subagents.map((agent) => {
    const startMs = Date.parse(agent.atUtc);

    return { agent, startMs, endMs: startMs + agent.lengthMs };
  });
}

export interface AgentTally {
  subagents: number;
  toolCalls: number;
  cost: number;
  faults: number;
}

export function tallyOf(stints: readonly Stint[]): AgentTally {
  return {
    subagents: stints.length,
    toolCalls: stints.reduce((sum, stint) => sum + stint.agent.toolCalls, 0),
    cost: stints.reduce((sum, stint) => sum + stint.agent.cost, 0),
    faults: stints.reduce((sum, stint) => sum + stint.agent.faults, 0),
  };
}

export function briefNote(agent: Subagent): string {
  return agent.brief === null ? 'The brief was not recorded.' : 'The rest of the brief was not recorded.';
}

export const noReport = 'This subagent wrote no report.';

// A Thin run has no Span to find a Subagent by, so it says so rather than reading as a run that had none.
export function noSubagentsWord(depth: Depth, inRun: number): string {
  if (depth === 'thin') {
    return 'A thin run cannot say which subagents it ran.';
  }

  return inRun === 0 ? 'No subagent ran in this run.' : 'No subagent ran in this stretch.';
}

export function ranByOne<T extends { step: { id: string } }>(
  marks: readonly T[],
  agents: Record<string, string>,
  agent: string | null,
): T[] {
  return agent === null ? [...marks] : marks.filter((mark) => agents[mark.step.id] === agent);
}
