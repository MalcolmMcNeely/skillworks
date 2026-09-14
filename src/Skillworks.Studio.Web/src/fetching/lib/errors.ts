export function describeFetchFailure(failure: unknown): string {
  return failure instanceof Error ? failure.message : 'Could not reach the API';
}
