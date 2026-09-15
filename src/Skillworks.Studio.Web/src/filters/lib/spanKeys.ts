import { dayMilliseconds, type Filter } from './filters';

export type SpanKey = '24h' | '7d' | '30d';

export const spanKeys: readonly { key: SpanKey; word: string; days: number }[] = [
  { key: '24h', word: '24H', days: 1 },
  { key: '7d', word: '7D', days: 7 },
  { key: '30d', word: '30D', days: 30 },
];

// UTC, because the Filter counts whole UTC days.
export function todayUtc(now: Date): string {
  return now.toISOString().slice(0, 10);
}

function daysBefore(day: string, days: number): string {
  return new Date(Date.parse(`${day}T00:00:00Z`) - days * dayMilliseconds).toISOString().slice(0, 10);
}

// Both dates every time, never the lookback, whose length the API decides and can change.
export function withSpanKey(filter: Filter, key: SpanKey, today: string): Filter {
  const days = spanKeys.find((span) => span.key === key)?.days ?? 1;

  return { ...filter, from: daysBefore(today, days - 1), to: today };
}

export function spanKeyOf(span: { from: string; to: string }, today: string): SpanKey | null {
  if (span.to !== today) {
    return null;
  }

  return spanKeys.find((key) => span.from === daysBefore(today, key.days - 1))?.key ?? null;
}
