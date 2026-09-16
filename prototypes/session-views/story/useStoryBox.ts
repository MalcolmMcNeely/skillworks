// PROTOTYPE — throwaway. Charts are drawn in pixels, so each one reads the size of the box it sits in.

import { useLayoutEffect, useRef, useState } from 'react';

export function useStoryBox<T extends HTMLElement>(fallbackWidth = 600, fallbackHeight = 300) {
  const ref = useRef<T>(null);
  const [box, setBox] = useState({ width: fallbackWidth, height: fallbackHeight });

  useLayoutEffect(() => {
    const element = ref.current;
    if (element === null) return;

    setBox({ width: element.clientWidth, height: element.clientHeight });
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width);
      const height = Math.round(entry.contentRect.height);
      setBox((last) => (last.width === width && last.height === height ? last : { width, height }));
    });
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  return [ref, box] as const;
}
