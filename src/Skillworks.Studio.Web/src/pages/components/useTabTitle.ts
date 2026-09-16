import { useEffect } from 'react';

// A rendered <title> would be hoisted after the document's own, and the browser reads the first.
export function useTabTitle(title: string) {
  useEffect(() => {
    document.title = title;
  }, [title]);
}
