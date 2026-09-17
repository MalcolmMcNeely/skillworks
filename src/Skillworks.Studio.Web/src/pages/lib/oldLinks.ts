import { watch } from './pages';

// What an old link could hold: never skill, which the map never wrote, and still view, not figure.
const watchWords = ['from', 'to', 'repository', 'view', 'order'];

// A bookmark from before Watch had an address of its own still opens the map.
export function oldLinkRedirect(search: string): string | null {
  const params = new URLSearchParams(search);

  if (!watchWords.some((word) => params.has(word))) {
    return null;
  }

  // Passed on as written, as reading the search part back out would re-encode it.
  return `${watch.address}?${search.replace(/^\?/, '')}`;
}
