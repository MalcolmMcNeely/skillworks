import type { Gap, GapEnd } from '../../gaps/lib/gaps';

export interface Activation {
  skill: string;
  atUtc: string;
  session: string;
  repository: string | null;
  trigger: string | null;
}

export interface ActivationsPage {
  kind: 'activations';
  activations: Activation[];
}

export type ActivationsLine = ActivationsPage | GapEnd;

export interface ActivationsAnswer {
  activations: Activation[];
  // No firings yet is not the same as a skill that never fired, so the list waits for this.
  landed: boolean;
  gap: Gap | null;
}

export const noActivations: ActivationsAnswer = { activations: [], landed: false, gap: null };

export function foldActivationsLine(answer: ActivationsAnswer, line: ActivationsLine): ActivationsAnswer {
  if (line.kind === 'end') {
    // Landed either way: a store that fell short has said all it is going to say.
    return { ...answer, landed: true, gap: line.gap };
  }

  return { ...answer, activations: line.activations, landed: true };
}

// Only a complete answer may say a Skill fired in no run; every other Gap means the record is missing, not empty.
export function firedInNoRun(answer: ActivationsAnswer): boolean {
  return answer.landed && answer.activations.length === 0 && answer.gap?.kind === 'complete';
}

// UTC, as a local clock would list a late firing under the wrong day.
export function describeFiredAt(atUtc: string): string {
  return new Date(atUtc).toISOString().replace('T', ' ').slice(0, 16);
}
