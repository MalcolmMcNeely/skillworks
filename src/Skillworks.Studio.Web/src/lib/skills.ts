/** How a column reports itself: not sorted, or sorted one way. */
export type SortDirection = false | 'asc' | 'desc';

/**
 * The token counts a split cell reads. Declared here rather than taken from `api`, because lib is
 * the bottom of the stack and reaching up for a shape would point a dependency the wrong way.
 */
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

/**
 * How a set of repositories or branches reads in one cell. A skill that has never fired gets a dash
 * rather than an empty cell, so the row still reads as a row.
 */
export function describeList(values: readonly string[]): string {
  return values.length === 0 ? '—' : values.join(', ');
}

/**
 * How an amount of money reads in one cell. A cost the API could only partly work out is marked, so
 * a figure that is a floor is never read as the answer.
 */
export function describeMoney(amount: number, partial = false): string {
  return partial ? `${money.format(amount)}+` : money.format(amount);
}

/** How a count of tokens reads in one cell. */
function describeTokens(count: number): string {
  return tokens.format(count);
}

/**
 * The token split in one cell: input, output and the cache read and written. The thinking is left
 * out because it is already inside the output, and a reader would add it on.
 */
export function describeSplit(spend: TokenSplit): string {
  return [
    `in ${describeTokens(spend.inputTokens)}`,
    `out ${describeTokens(spend.outputTokens)}`,
    `cache ${describeTokens(spend.cacheReadTokens)}r`,
    `${describeTokens(spend.cacheWriteTokens)}w`,
  ].join(' · ');
}

/** The arrow that goes beside a column heading. Nothing at all when the column is not sorted. */
export function sortMark(sorted: SortDirection): string {
  if (sorted === 'asc') {
    return ' ▲';
  }

  return sorted === 'desc' ? ' ▼' : '';
}

/** The same fact again, for a screen reader rather than an eye. */
export function ariaSort(sorted: SortDirection): 'ascending' | 'descending' | 'none' {
  if (sorted === 'asc') {
    return 'ascending';
  }

  return sorted === 'desc' ? 'descending' : 'none';
}
