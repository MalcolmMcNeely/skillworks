// PROTOTYPE — throwaway. Small pieces every part of the Scrub variant leans on: the brushed range, element size and
// callbacks that keep one identity, so memoised tabs do not redraw on every cursor move.

import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import type { Session } from '../sessionModel';

export type Range = [number, number];

export type ScrubTab = 'trace' | 'skills' | 'conversation' | 'time' | 'context';

export const settings = {
  prompts: 'OTEL_LOG_USER_PROMPTS',
  responses: 'OTEL_LOG_ASSISTANT_RESPONSES',
  toolContent: 'OTEL_LOG_TOOL_CONTENT',
};

export function useSize<T extends Element>() {
  const ref = useRef<T>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    const node = ref.current;
    if (node === null) return;
    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: Math.round(entry.contentRect.width), height: Math.round(entry.contentRect.height) });
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return [ref, size] as const;
}

export function useStable<A extends unknown[], R>(fn: (...args: A) => R): (...args: A) => R {
  const latest = useRef(fn);

  useLayoutEffect(() => {
    latest.current = fn;
  });

  return useCallback((...args: A) => latest.current(...args), []);
}

// Padded, so the step the reader asked for never sits flush against the edge of the lanes.
export function windowAround(startMs: number, endMs: number, session: Session, least = 20_000): Range {
  const pad = Math.max(least, (endMs - startMs) * 0.08);
  return [Math.max(session.startMs, startMs - pad), Math.min(session.endMs, endMs + pad)];
}

export const overlaps = (startMs: number, endMs: number, range: Range | null) => range === null || (endMs >= range[0] && startMs <= range[1]);

// A log scale, so a two-minute question and an eleven-hour day both leave a visible bar.
export const lengthShare = (ms: number) => Math.max(0.03, Math.min(1, Math.log10(ms / 1000 + 1) / Math.log10(12 * 3600 + 1)));

export function niceMax(value: number) {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
    if (step * power >= value) return step * power;
  }
  return 10 * power;
}

export const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value));
