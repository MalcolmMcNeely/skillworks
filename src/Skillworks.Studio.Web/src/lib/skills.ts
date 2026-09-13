/**
 * How a set of repositories or branches reads in one cell. A skill that has never fired gets a dash
 * rather than an empty cell, so the row still reads as a row.
 */
export function describeList(values: readonly string[]): string {
  return values.length === 0 ? '—' : values.join(', ');
}
