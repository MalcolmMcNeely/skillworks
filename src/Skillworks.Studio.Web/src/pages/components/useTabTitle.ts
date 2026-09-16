import { useEffect } from 'react';
import type { Page } from '../lib/pages';

// A rendered <title> would be hoisted after the document's own, and the browser reads the first.
export function useTabTitle(page: Page) {
  useEffect(() => {
    document.title = page.tabTitle;
  }, [page]);
}
