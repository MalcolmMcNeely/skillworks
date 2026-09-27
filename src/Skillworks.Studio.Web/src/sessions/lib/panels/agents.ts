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

export function ranByOne<T extends { step: { id: string } }>(
  marks: readonly T[],
  agents: Record<string, string>,
  agent: string | null,
): T[] {
  return agent === null ? [...marks] : marks.filter((mark) => agents[mark.step.id] === agent);
}
