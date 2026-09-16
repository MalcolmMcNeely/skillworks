export interface SkillCall {
  id: string;
  skill: string;
  atUtc: string;
  // No event says a Skill finished, so this runs to the next Skill call or to the end of the run.
  followedMs: number;
  trigger: string | null;
}

export interface SkillCallsPage {
  kind: 'skillCalls';
  skillCalls: SkillCall[];
}

export interface Firing {
  call: SkillCall;
  atMs: number;
  followedToMs: number;
}

export function firingsOf(calls: readonly SkillCall[]): Firing[] {
  return calls.map((call) => {
    const atMs = Date.parse(call.atUtc);

    return { call, atMs, followedToMs: atMs + call.followedMs };
  });
}

export interface Tally {
  calls: number;
  // Distinct, so a run that leaned on one Skill reads apart from one that used many.
  skills: number;
}

export function tallyOf(firings: readonly Firing[]): Tally {
  return { calls: firings.length, skills: new Set(firings.map((firing) => firing.call.skill)).size };
}
