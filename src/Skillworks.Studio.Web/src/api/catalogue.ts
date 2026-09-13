/** The shape `GET /api/catalogue` returns. */
export interface CatalogueLocation {
  path: string;
  exists: boolean;
}

export async function fetchCatalogue(signal: AbortSignal): Promise<CatalogueLocation> {
  const response = await fetch('/api/catalogue', { signal });

  if (!response.ok) {
    throw new Error(`GET /api/catalogue returned ${response.status}`);
  }

  return (await response.json()) as CatalogueLocation;
}
