import type { Filter } from './filters';

export type DepthKey = '' | 'full' | 'thin';

export const depthKeys: readonly { key: DepthKey; word: string }[] = [
  { key: '', word: 'Any' },
  { key: 'full', word: 'Full' },
  { key: 'thin', word: 'Thin' },
];

// The address bar can name a Depth nobody has, and a pressed key would then claim a narrowing the table has not got.
export function depthKeyOf(filter: Filter): DepthKey | null {
  return depthKeys.find((depth) => depth.key === filter.depth)?.key ?? null;
}

// The API lists both depths for a Depth it cannot read, so a misspelled one has narrowed nothing to explain.
export function narrowsByDepth(filter: Filter): boolean {
  const key = depthKeyOf(filter);

  return key !== null && key !== '';
}
