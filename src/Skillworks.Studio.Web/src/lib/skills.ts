/** How a column reports itself: not sorted, or sorted one way. */
export type SortDirection = false | 'asc' | 'desc';

/**
 * How a set of repositories or branches reads in one cell. A skill that has never fired gets a dash
 * rather than an empty cell, so the row still reads as a row.
 */
export function describeList(values: readonly string[]): string {
  return values.length === 0 ? '—' : values.join(', ');
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
