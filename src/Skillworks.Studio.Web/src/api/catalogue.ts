import { getJson } from './json';

/** The shape `GET /api/catalogue` returns. */
export interface CatalogueLocation {
  path: string;
  exists: boolean;
}

export function fetchCatalogue(signal: AbortSignal): Promise<CatalogueLocation> {
  return getJson<CatalogueLocation>('/api/catalogue', signal);
}
