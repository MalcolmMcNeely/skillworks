import type { Gap } from '../../gaps/lib/gaps';
import type { Origin } from '../../provenance/lib/provenance';
import type { SkillOnDay, SkillsHead, SkillsLine, SkillSummary, TurnTotals } from './skills';
import { totalsOf, type Totals } from './totals';

export interface SkillsAnswer {
  span: SkillsHead['span'];
  landedDays: string[];
  skills: SkillSummary[];
  unnamedSpend: TurnTotals | null;
  totals: Totals;
  arriving: boolean;
  // Null while arriving, as whether the answer fell short is known only once its last day lands.
  gap: Gap | null;
  // The first day that names one replaces its zero rather than adding to it, as the zero named no Turns.
  catalogueAtZero: string[];
}

const nothingSpent: TurnTotals = { inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, cacheCreationTokens: 0, cost: 0 };

// No Each with no Activations to share the Cost across, or with a Cost that went unnamed.
function summaryOf(skill: SkillOnDay): SkillSummary {
  return { ...skill, each: skill.spend === null || skill.activations === 0 ? null : skill.spend.cost / skill.activations };
}

// Unnamed only while neither side named the spend.
function plus(spend: TurnTotals | null, more: TurnTotals | null): TurnTotals | null {
  if (spend === null || more === null) {
    return spend ?? more;
  }

  return {
    inputTokens: spend.inputTokens + more.inputTokens,
    outputTokens: spend.outputTokens + more.outputTokens,
    cacheReadTokens: spend.cacheReadTokens + more.cacheReadTokens,
    cacheCreationTokens: spend.cacheCreationTokens + more.cacheCreationTokens,
    cost: spend.cost + more.cost,
  };
}

function sortedUnion(names: readonly string[] | null, more: readonly string[] | null): string[] {
  return [...new Set([...(names ?? []), ...(more ?? [])])].toSorted();
}

// As the API orders them, an absent name first, so a skill's Origins read the same however many days they span.
function ignoringCase(name: string | null, other: string | null): number {
  if (name === null || other === null) {
    return name === other ? 0 : name === null ? -1 : 1;
  }

  const [upper, otherUpper] = [name.toUpperCase(), other.toUpperCase()];

  return upper === otherUpper ? 0 : upper < otherUpper ? -1 : 1;
}

function orderedOrigins(origins: readonly Origin[], more: readonly Origin[]): Origin[] {
  const distinct = new Map<string, Origin>();

  for (const origin of [...origins, ...more]) {
    distinct.set(JSON.stringify([origin.trigger, origin.source, origin.plugin, origin.marketplace]), origin);
  }

  return [...distinct.values()].toSorted(
    (a, b) =>
      ignoringCase(a.marketplace, b.marketplace) || ignoringCase(a.plugin, b.plugin) || ignoringCase(a.trigger, b.trigger),
  );
}

function added(landed: SkillSummary, skill: SkillOnDay): SkillSummary {
  const spend = plus(landed.spend, skill.spend);

  return summaryOf({
    name: landed.name,
    activations: landed.activations + skill.activations,
    repositories: sortedUnion(landed.repositories, skill.repositories),
    models: spend === null ? null : sortedUnion(landed.models, skill.models),
    efforts: spend === null ? null : sortedUnion(landed.efforts, skill.efforts),
    spend,
    origins: orderedOrigins(landed.origins, skill.origins),
  });
}

function withTotals(answer: Omit<SkillsAnswer, 'totals'>): SkillsAnswer {
  return { ...answer, totals: totalsOf(answer) };
}

// The catalogue's zeros land with the head, and shown before a day or after an outage they would read as a quiet week.
export function showsFigures(answer: SkillsAnswer | null): answer is SkillsAnswer {
  return answer !== null && answer.landedDays.length > 0 && answer.gap?.kind !== 'unreachable';
}

export function foldSkillsLine(answer: SkillsAnswer | null, line: SkillsLine): SkillsAnswer {
  if (line.kind === 'head') {
    return withTotals({
      span: line.span,
      landedDays: [],
      skills: line.catalogueSkills.map((name) =>
        summaryOf({ name, activations: 0, repositories: [], models: [], efforts: [], spend: nothingSpent, origins: [] }),
      ),
      unnamedSpend: null,
      arriving: true,
      gap: null,
      catalogueAtZero: line.catalogueSkills,
    });
  }

  if (answer === null) {
    throw new Error(`A skills answer starts with its head, not a ${line.kind} line.`);
  }

  if (line.kind === 'end') {
    return { ...answer, arriving: false, gap: line.gap };
  }

  const skills = new Map(answer.skills.map((skill) => [skill.name, skill]));

  for (const skill of line.skills) {
    const landed = skills.get(skill.name);

    skills.set(
      skill.name,
      landed === undefined || answer.catalogueAtZero.includes(skill.name) ? summaryOf(skill) : added(landed, skill),
    );
  }

  return withTotals({
    ...answer,
    landedDays: [...answer.landedDays, line.day],
    skills: [...skills.values()].toSorted((a, b) => a.name.localeCompare(b.name)),
    unnamedSpend: plus(answer.unnamedSpend, line.unnamedSpend),
    catalogueAtZero: answer.catalogueAtZero.filter((name) => !line.skills.some((skill) => skill.name === name)),
  });
}
