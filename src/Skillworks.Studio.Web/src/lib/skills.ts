export type SortDirection = false | 'asc' | 'desc';

export interface TokenSplit {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
}

// Pinned to one locale rather than the reader's, because the price table is in US dollars and a
// figure that reads as dollars should be grouped and pointed the way dollars are.
const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  // Four places, because a cheap skill on a cheap model can cost a fraction of a cent a firing and
  // rounding it to the penny would report it as free.
  maximumFractionDigits: 4,
});

const tokens = new Intl.NumberFormat('en-US');

export function describeList(values: readonly string[]): string {
  return values.length === 0 ? '—' : values.join(', ');
}

export function describeMoney(amount: number, partial = false): string {
  return partial ? `${money.format(amount)}+` : money.format(amount);
}

function describeTokens(count: number): string {
  return tokens.format(count);
}

export function describeSplit(spend: TokenSplit): string {
  return [
    `in ${describeTokens(spend.inputTokens)}`,
    `out ${describeTokens(spend.outputTokens)}`,
    `cache ${describeTokens(spend.cacheReadTokens)}r`,
    `${describeTokens(spend.cacheWriteTokens)}w`,
  ].join(' · ');
}

export function sortMark(sorted: SortDirection): string {
  if (sorted === 'asc') {
    return ' ▲';
  }

  return sorted === 'desc' ? ' ▼' : '';
}

export function ariaSort(sorted: SortDirection): 'ascending' | 'descending' | 'none' {
  if (sorted === 'asc') {
    return 'ascending';
  }

  return sorted === 'desc' ? 'descending' : 'none';
}
