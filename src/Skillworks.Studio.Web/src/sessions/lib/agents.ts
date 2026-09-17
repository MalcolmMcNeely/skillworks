import type { Gap, Signal } from '../../gaps/lib/gaps';
import { notKnown } from './sessions';

export type Depth = 'thin' | 'full';

export interface AgentsPage {
  kind: 'agents';
  depth: Depth;
  // Only the Steps a Subagent ran, as the browser is sent a Session and never a Span.
  agents: Record<string, string>;
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
