import { inSpell, madeIn, type Spell } from './view';
import { highlightKey, skillLabelOf, type Highlight } from './highlight';
import { isAttributed, type Mark, type Step } from '../steps';
import type { ActivationSpell } from './activations';

export type SkillKey = Exclude<Highlight, { kind: 'tool' }>;

export interface SkillRow {
  key: SkillKey;
  label: string;
  fired: number | null;
  turns: number;
  toolCalls: number;
  cost: number;
  lengthMs: number;
}

function keyOf(step: Step): SkillKey {
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
): SkillRow[] {
  const fired = madeIn(spells, view);
  const rows = new Map<string, SkillRow>();

  for (const { step } of inSpell(marks, view)) {
    if (!isAttributed(step)) {
      continue;
    }

    const key = keyOf(step);
    const heldAs = highlightKey(key);
    const row = rows.get(heldAs) ?? {
      key,
      label: skillLabelOf(key),
      fired: key.kind === 'skill' ? fired.filter((spell) => spell.activation.skill === key.name).length : null,
      turns: 0,
      toolCalls: 0,
      cost: 0,
      lengthMs: 0,
    };

    rows.set(heldAs, {
      ...row,
      turns: row.turns + (step.kind === 'turn' ? 1 : 0),
      toolCalls: row.toolCalls + (step.kind === 'turn' ? 0 : 1),
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
