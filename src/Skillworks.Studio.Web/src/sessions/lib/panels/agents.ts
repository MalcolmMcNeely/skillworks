import type { Gap, GapKind, Signal } from '../../../shared/gaps/lib/gaps';
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
  // The Spans half alone, because only a Span names an agent, and withheld words leave those Spans standing.
  traced: boolean;
  // Only the Steps a Subagent ran, as the browser is sent a Session and never a Span.
  agents: Record<string, string>;
  subagents: Subagent[];
}

export const mainAgent = 'Main agent';

// A run with no Span has none to name the agent, so it reads not known rather than as the main agent's work.
export function ranBy(traced: boolean, agents: Record<string, string>, step: string): string {
  return traced ? (agents[step] ?? mainAgent) : notKnown;
}

export function describeDepth(depth: Depth): string {
  return depth === 'full' ? 'Full' : 'Thin';
}

// Every kind is answered here, so a kind added later cannot fall quietly to the tone for a store that held nothing.
const thinTones: Record<GapKind, Signal['tone']> = {
  complete: 'quiet',
  unreachable: 'failed',
  shortened: 'failed',
  telemetryOff: 'quiet',
  telemetryUnknown: 'quiet',
  wordsOff: 'quiet',
  quiet: 'quiet',
};

// A run still arriving is Thin and not yet short of anything, so only a store that fell short reads failed.
export function depthTone(depth: Depth, gap: Gap | null): Signal['tone'] {
  if (depth === 'full') {
    return 'live';
  }

  return gap === null ? 'quiet' : thinTones[gap.kind];
}

export interface AgentSpell {
  agent: Subagent;
  startMs: number;
  endMs: number;
}

export function agentSpellsOf(subagents: readonly Subagent[]): AgentSpell[] {
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

export function tallyOf(spells: readonly AgentSpell[]): AgentTally {
  return {
    subagents: spells.length,
    toolCalls: spells.reduce((sum, spell) => sum + spell.agent.toolCalls, 0),
    cost: spells.reduce((sum, spell) => sum + spell.agent.cost, 0),
    faults: spells.reduce((sum, spell) => sum + spell.agent.faults, 0),
  };
}

export function briefNote(agent: Subagent): string {
  return agent.brief === null ? 'The brief was not recorded.' : 'The rest of the brief was not recorded.';
}

export const noReport = 'This subagent wrote no report.';

// A run with no Span has none to find a Subagent by, so it says so rather than reading as a run that had none.
export function noSubagentsWord(traced: boolean, inRun: number): string {
  if (!traced) {
    return 'A run with no spans cannot say which subagents it ran.';
  }

  return inRun === 0 ? 'No subagent ran in this run.' : 'No subagent ran in view.';
}

export function ranByOne<T extends { step: { id: string } }>(
  marks: readonly T[],
  agents: Record<string, string>,
  agent: string | null,
): T[] {
  return agent === null ? [...marks] : marks.filter((mark) => agents[mark.step.id] === agent);
}
