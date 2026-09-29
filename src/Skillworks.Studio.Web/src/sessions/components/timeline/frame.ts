import { useLayoutEffect, useRef, useState } from 'react';

// One gutter for every strip and chart on the axis, so the lane names line up and a moment sits at one x down the page.
export const gutter = 116;

const leastWidth = 360;

export function useWidth<T extends Element>() {
  const frame = useRef<T>(null);
  const [width, setWidth] = useState(leastWidth);

  useLayoutEffect(() => {
    const node = frame.current;

    if (node === null) {
      return;
    }

    const watching = new ResizeObserver(([entry]) => setWidth(Math.max(leastWidth, Math.round(entry.contentRect.width))));

    watching.observe(node);

    return () => watching.disconnect();
  }, []);

  return [frame, width] as const;
}
