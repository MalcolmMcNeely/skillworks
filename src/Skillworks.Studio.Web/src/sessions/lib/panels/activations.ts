export interface Activation {
  id: string;
  skill: string;
  atUtc: string;
  // No event says a Skill finished, so this runs to the next Activation or to the end of the run.
  followedMs: number;
  trigger: string | null;
}

export interface ActivationsPage {
  kind: 'activations';
  activations: Activation[];
}

export interface ActivationSpell {
  activation: Activation;
  atMs: number;
  followedToMs: number;
}

export function activationSpellsOf(activations: readonly Activation[]): ActivationSpell[] {
  return activations.map((activation) => {
    const atMs = Date.parse(activation.atUtc);

    return { activation, atMs, followedToMs: atMs + activation.followedMs };
  });
}

export interface Tally {
  activations: number;
  // Distinct, so a run that leaned on one Skill reads apart from one that used many.
  skills: number;
}

export function tallyOf(spells: readonly ActivationSpell[]): Tally {
  return { activations: spells.length, skills: new Set(spells.map((spell) => spell.activation.skill)).size };
}
