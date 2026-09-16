import { watch } from './pages';

// Not skill: the map never wrote one, so a link naming only that was never a map link.
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
