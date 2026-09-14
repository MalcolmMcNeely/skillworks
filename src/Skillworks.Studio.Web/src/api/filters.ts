import { getJson } from './json';

// Read from the whole history, so a filter that has emptied the table still offers the way back.
export interface FilterChoices {
  repositories: string[];
  skills: string[];
}

export function fetchFilters(signal?: AbortSignal): Promise<FilterChoices> {
  return getJson<FilterChoices>('/api/filters', signal);
}
