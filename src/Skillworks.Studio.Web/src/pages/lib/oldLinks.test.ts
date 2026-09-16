import { describe, expect, it } from 'vitest';
import { oldLinkRedirect } from './oldLinks';

describe('oldLinkRedirect', () => {
  it.each(['from=2026-09-01', 'to=2026-09-07', 'repository=skillworks', 'view=activations', 'order=least'])(
    'sends a link that names %s on to Watch, so a bookmark from before Watch had an address still works',
    (search) => {
      expect(oldLinkRedirect(`?${search}`)).toBe(`/watch?${search}`);
    },
  );

  it('keeps every word of the old link, in the order it was written', () => {
    expect(oldLinkRedirect('?view=activations&from=2026-09-01&repository=skillworks&order=least&to=2026-09-07')).toBe(
      '/watch?view=activations&from=2026-09-01&repository=skillworks&order=least&to=2026-09-07',
    );
  });

  it('takes a search part written without its question mark', () => {
    expect(oldLinkRedirect('from=2026-09-01')).toBe('/watch?from=2026-09-01');
  });

  it.each(['', '?'])('leaves a plain address alone, so Studio opens on Home', (search) => {
    expect(oldLinkRedirect(search)).toBeNull();
  });

  it('leaves an address that names only other words alone', () => {
    expect(oldLinkRedirect('?skill=implement')).toBeNull();
  });

  it('leaves an address whose word only begins with one of Watch’s alone', () => {
    expect(oldLinkRedirect('?fromage=brie')).toBeNull();
  });

  it('leaves an address that carries one of Watch’s words as a value alone', () => {
    expect(oldLinkRedirect('?skill=from')).toBeNull();
  });

  it('passes an encoded character on unchanged, so the value it stands for is not lost', () => {
    expect(oldLinkRedirect('?repository=my%2Frepo+one')).toBe('/watch?repository=my%2Frepo+one');
  });
});
