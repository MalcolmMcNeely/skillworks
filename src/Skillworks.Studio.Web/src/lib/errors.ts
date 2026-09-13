/**
 * What to show a developer when a fetch did not come back. An Error carries a message worth
 * reading; anything else is a thrown value with nothing useful in it, so name the likely cause.
 */
export function describeFetchFailure(failure: unknown): string {
  return failure instanceof Error ? failure.message : 'Could not reach the API';
}
