import type { PlainEnd } from '../../gaps/lib/gaps';

export interface FilterChoicesHead {
  kind: 'head';
}

export interface FilterChoicesDay {
  kind: 'day';
  day: string;
  repositories: string[];
}

export type FilterChoicesLine = FilterChoicesHead | FilterChoicesDay | PlainEnd;

// As the API orders them, ignoring case, so an owner spelled with a capital does not jump ahead of the rest.
function ignoringCase(repository: string, other: string): number {
  const [upper, otherUpper] = [repository.toUpperCase(), other.toUpperCase()];

  return upper === otherUpper ? 0 : upper < otherUpper ? -1 : 1;
}

export function foldFilterChoicesLine(repositories: readonly string[], line: FilterChoicesLine): string[] {
  if (line.kind !== 'day') {
    return [...repositories];
  }

  return [...new Set([...repositories, ...line.repositories])].toSorted(ignoringCase);
}
