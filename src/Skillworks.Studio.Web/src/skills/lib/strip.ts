import type { SymbolTable } from '../../alphabets/lib/alphabets';
import { describeCount } from '../../figures/lib/figures';
import { describeDay } from '../../filters/lib/filters';
import type { SkillsDay, SkillsHead } from './skills';

const hoursInDay = 24;

// A missing slice is drawn like an idle one, so only the mark tells the two apart.
export const sliceGlyphs = { missing: '✕' } as const;

export const sliceSymbols: SymbolTable = { alphabet: 'condition', glyphs: Object.values(sliceGlyphs) };

export type StripSlice = {
  day: string;
  startHour: number;
  lengthInHours: number;
} & (
  | { state: 'landed'; activations: number }
  // No count, as a slice the store has not given is not a quiet one.
  | { state: 'arriving' | 'missing'; activations: null }
);

// A slice never crosses midnight, so each one lands with its day.
function hoursPerSlice(dayCount: number): number {
  if (dayCount <= 1) {
    return 1;
  }

  return dayCount <= 7 ? 6 : hoursInDay;
}

// Oldest first, as time runs left to right.
export function slicesOf(days: readonly string[]): StripSlice[] {
  const lengthInHours = hoursPerSlice(days.length);

  return days.toReversed().flatMap((day) =>
    Array.from({ length: hoursInDay / lengthInHours }, (_, index) => ({
      day,
      startHour: index * lengthInHours,
      lengthInHours,
      state: 'arriving' as const,
      activations: null,
    })),
  );
}

function inSlice(slice: StripSlice, hours: readonly number[]): number {
  return hours.slice(slice.startHour, slice.startHour + slice.lengthInHours).reduce((sum, count) => sum + count, 0);
}

export function withDayLanded(slices: readonly StripSlice[], line: SkillsDay): StripSlice[] {
  return slices.map((slice) =>
    slice.day !== line.day
      ? slice
      : {
          ...slice,
          state: 'landed',
          activations: line.skills.reduce((sum, skill) => sum + inSlice(slice, skill.hours), 0),
        },
  );
}

// One count per slice of the strip, so a tile's chart and the strip above it cut the span the same way.
export function withHoursLanded(
  counts: readonly number[],
  slices: readonly StripSlice[],
  day: string,
  hours: readonly number[],
): number[] {
  return slices.map((slice, index) => (slice.day === day ? inSlice(slice, hours) : (counts[index] ?? 0)));
}

export function withDaysMissing(slices: readonly StripSlice[], missingDays: readonly string[]): StripSlice[] {
  return slices.map((slice) =>
    slice.state === 'arriving' && missingDays.includes(slice.day) ? { ...slice, state: 'missing' } : slice,
  );
}

function hourWord(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`;
}

// One format for every instant, so two of them compare as text.
export function startOfHour(day: string, hour: number): string {
  return `${day}T${hourWord(hour)}:00Z`;
}

// The whole reading in words, because a screen reader sees neither a slice's height nor its outline.
export function describeSlice(slice: StripSlice): string {
  const when = slice.lengthInHours === hoursInDay ? describeDay(slice.day) : `${describeDay(slice.day)} ${hourWord(slice.startHour)}`;

  if (slice.state === 'landed') {
    return `${when} UTC. Activations ${describeCount(slice.activations)}.`;
  }

  return `${when} UTC. ${slice.state === 'arriving' ? 'Arriving' : 'Missing'}.`;
}

export interface StripLabel {
  at: number;
  text: string;
}

// Few enough that no two labels overlap, however long the span.
export function stripLabels(slices: readonly StripSlice[]): StripLabel[] {
  const lengthInHours = slices[0]?.lengthInHours ?? hoursInDay;
  const perDay = hoursInDay / lengthInHours;
  const everyDays = lengthInHours < hoursInDay ? 1 : 7 * Math.ceil(slices.length / 56);

  return slices.flatMap((slice, index) => {
    const at = index / slices.length;

    if (lengthInHours === 1) {
      return slice.startHour % 6 === 0 ? [{ at, text: hourWord(slice.startHour) }] : [];
    }

    return slice.startHour === 0 && (index / perDay) % everyDays === 0 ? [{ at, text: describeDay(slice.day) }] : [];
  });
}

// Null outside the span, as the strip shows no time to point at there.
export function nowAt(span: Pick<SkillsHead['span'], 'fromUtc' | 'untilUtc'>, now: number): number | null {
  const [from, until] = [Date.parse(span.fromUtc), Date.parse(span.untilUtc)];

  return now < from || now >= until ? null : (now - from) / (until - from);
}
