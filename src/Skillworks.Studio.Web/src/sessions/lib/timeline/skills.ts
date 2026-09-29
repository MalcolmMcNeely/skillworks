import { inSpell, madeIn, type Spell } from './view';
import { highlightKey, skillLabelOf, type Highlight } from './highlight';
import { isAttributed, isToolCall, type Mark, type Step } from '../steps';
import type { ActivationSpell } from './activations';

export type SkillKey = Exclude<Highlight, { kind: 'tool' }>;

export interface SkillRow {
  key: SkillKey;
  label: string;
  // Every agent's, even with a Subagent open, as an Activation names no agent.
  activations: number | null;
  turns: number;
  // Null in a Session with no Spans, where a count would pass off the calls whose skill is not known.
  toolCalls: number | null;
  cost: number;
  lengthMs: number;
}

export function skillKeyOf(step: Step): SkillKey {
  if (step.unnamed) {
    return { kind: 'unnamed' };
  }

  return step.skill === null ? { kind: 'noSkill' } : { kind: 'skill', name: step.skill };
}

// Named skills first, then the two rows that belong to no named skill, so those never push a skill off the top.
const place = { skill: 0, noSkill: 1, unnamed: 2 } as const;

export function costIn(marks: readonly Mark[], view: Spell | null): number {
  return inSpell(marks, view).reduce((sum, { step }) => sum + step.cost, 0);
}

// Found by the Attribution each Step carries, so a skill that called another counts none of the other's Steps.
export function skillRowsOf(
  marks: readonly Mark[],
  spells: readonly ActivationSpell[],
  view: Spell | null,
  // An open Subagent's Activations cannot be told apart, so the count stays the whole run's, View and all.
  wholeRun = false,
): SkillRow[] {
  const shownSpells = wholeRun ? spells : madeIn(spells, view);
  const shown = inSpell(marks, view);
  const callsKnown = shown.every(({ step }) => !isToolCall(step) || step.skillKnown);
  const rows = new Map<string, SkillRow>();

  for (const { step } of shown) {
    if (!isAttributed(step)) {
      continue;
    }

    const key = skillKeyOf(step);
    const heldAs = highlightKey(key);
    const row = rows.get(heldAs) ?? {
      key,
      label: skillLabelOf(key),
      activations: key.kind === 'skill' ? shownSpells.filter((spell) => spell.activation.skill === key.name).length : null,
      turns: 0,
      toolCalls: callsKnown ? 0 : null,
      cost: 0,
      lengthMs: 0,
    };

    rows.set(heldAs, {
      ...row,
      turns: row.turns + (step.kind === 'turn' ? 1 : 0),
      toolCalls: row.toolCalls === null ? null : row.toolCalls + (step.kind === 'turn' ? 0 : 1),
      cost: row.cost + step.cost,
      lengthMs: row.lengthMs + step.lengthMs,
    });
  }

  // By name within a tie, so two reads of one run list the rows the same way.
  return [...rows.values()].toSorted(
    (one, other) =>
      place[one.key.kind] - place[other.key.kind] || other.cost - one.cost || one.label.localeCompare(other.label, 'en'),
  );
}
