import type { Gap } from '../../shared/gaps/lib/gaps';
import type { Origin, TriggerCount } from '../../shared/provenance/lib/provenance';
import type { SkillOnDay, SkillsHead, SkillsLine, SkillSummary, TurnTotals } from './skills';
import { slicesOf, startOfHour, withDaysMissing, withDayLanded, withHoursLanded, type StripSlice } from './strip';
import { totalsOf, type Totals } from './totals';

export interface SkillsAnswer {
  span: SkillsHead['span'];
  days: string[];
  landedDays: string[];
  // Named once the answer ends, as a day still to come may yet land.
  missingDays: string[];
  slices: StripSlice[];
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

type SkillFigures = Omit<SkillOnDay, 'hours'>;

function lastFiredOn(day: string, hours: readonly number[]): string | null {
  const hour = hours.findLastIndex((count) => count > 0);

  return hour < 0 ? null : startOfHour(day, hour);
}

function later(instant: string | null, other: string | null): string | null {
  return instant === null || (other !== null && other > instant) ? other : instant;
}

// No Each with no Activations to share the Cost across, or with a Cost that went unnamed.
function summaryOf(skill: SkillFigures, lastFired: string | null, spark: number[]): SkillSummary {
  return {
    ...skill,
    each: skill.spend === null || skill.activations === 0 ? null : skill.spend.cost / skill.activations,
    lastFired,
    spark,
  };
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

// Re-sorted, so a skill's triggers read the same however many days it spans.
function addedTriggers(counts: readonly TriggerCount[], more: readonly TriggerCount[]): TriggerCount[] {
  const summed = new Map<string | null, number>();

  for (const count of [...counts, ...more]) {
    summed.set(count.trigger, (summed.get(count.trigger) ?? 0) + count.activations);
  }

  return [...summed]
    .map(([trigger, activations]) => ({ trigger, activations }))
    .toSorted((a, b) => ignoringCase(a.trigger, b.trigger));
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

function added(landed: SkillSummary, skill: SkillFigures, lastFired: string | null, spark: number[]): SkillSummary {
  const spend = plus(landed.spend, skill.spend);

  return summaryOf(
    {
      name: landed.name,
      activations: landed.activations + skill.activations,
      triggers: addedTriggers(landed.triggers, skill.triggers),
      repositories: sortedUnion(landed.repositories, skill.repositories),
      models: spend === null ? null : sortedUnion(landed.models, skill.models),
      efforts: spend === null ? null : sortedUnion(landed.efforts, skill.efforts),
      spend,
      origins: orderedOrigins(landed.origins, skill.origins),
    },
    later(landed.lastFired, lastFired),
    spark,
  );
}

function withTotals(answer: Omit<SkillsAnswer, 'totals'>): SkillsAnswer {
  return { ...answer, totals: totalsOf(answer) };
}

// The catalogue's zeros land with the head, and shown before a day lands they would read as a quiet week.
export function showsFigures(answer: SkillsAnswer | null): answer is SkillsAnswer {
  return answer !== null && answer.landedDays.length > 0;
}

export function foldSkillsLine(answer: SkillsAnswer | null, line: SkillsLine): SkillsAnswer {
  if (line.kind === 'head') {
    const slices = slicesOf(line.days);

    return withTotals({
      span: line.span,
      days: line.days,
      landedDays: [],
      missingDays: [],
      slices,
      skills: line.catalogueSkills.map((name) =>
        summaryOf(
          { name, activations: 0, triggers: [], repositories: [], models: [], efforts: [], spend: nothingSpent, origins: [] },
          null,
          slices.map(() => 0),
        ),
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
    const missingDays = answer.days.filter((day) => !answer.landedDays.includes(day));

    return {
      ...answer,
      missingDays,
      slices: withDaysMissing(answer.slices, missingDays),
      arriving: false,
      gap: line.gap,
    };
  }

  const skills = new Map(answer.skills.map((skill) => [skill.name, skill]));
  const nothingYet = answer.slices.map(() => 0);

  for (const { hours, ...figures } of line.skills) {
    const landed = skills.get(figures.name);
    const earlier = landed === undefined || answer.catalogueAtZero.includes(figures.name) ? null : landed;
    const lastFired = lastFiredOn(line.day, hours);
    const spark = withHoursLanded(earlier?.spark ?? nothingYet, answer.slices, line.day, hours);

    skills.set(
      figures.name,
      earlier === null ? summaryOf(figures, lastFired, spark) : added(earlier, figures, lastFired, spark),
    );
  }

  return withTotals({
    ...answer,
    landedDays: [...answer.landedDays, line.day],
    slices: withDayLanded(answer.slices, line),
    skills: [...skills.values()].toSorted((a, b) => a.name.localeCompare(b.name)),
    unnamedSpend: plus(answer.unnamedSpend, line.unnamedSpend),
    catalogueAtZero: answer.catalogueAtZero.filter((name) => !line.skills.some((skill) => skill.name === name)),
  });
}
