import { getJson } from './json';

/**
 * `GET /api/filters`: what the three filters can be narrowed to. Read from the whole history rather
 * than from the narrowed answer, so a filter that has emptied the table still offers the way back.
 */
export interface FilterChoices {
  repositories: string[];
  skills: string[];
}

export function fetchFilters(signal?: AbortSignal): Promise<FilterChoices> {
  return getJson<FilterChoices>('/api/filters', signal);
}
