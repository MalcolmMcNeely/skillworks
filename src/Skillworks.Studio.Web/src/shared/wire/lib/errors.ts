// Not a Gap word: the API did not answer, and the store behind it may be fine.
export const noLink = 'No link';

export function describeFetchFailure(failure: unknown): string {
  return failure instanceof Error ? failure.message : 'Could not reach the API';
}
