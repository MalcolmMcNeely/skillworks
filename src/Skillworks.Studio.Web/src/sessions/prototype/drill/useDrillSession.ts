// PROTOTYPE — throwaway. Variant A's measures, worked out once per session, and the width of a chart's box.

import { useEffect, useMemo, useState, type RefObject } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import { activations, contextSeries, conversation, findings, summarize, timeSplit, type ContextPoint, type Finding } from '../sessionMeasures';

export function useDrillSession(session: Session | null) {
  return useMemo(
    () =>
      session === null
        ? null
        : {
            summary: summarize(session),
            split: timeSplit(session),
            context: contextSeries(session),
            activations: activations(session),
            exchanges: conversation(session),
            findings: findings(session),
            byId: new Map(session.steps.map((step) => [step.id, step])),
          },
    [session],
  );
}

export type DrillMeasures = NonNullable<ReturnType<typeof useDrillSession>>;

// Two findings carry no steps of their own, so the chip lights the steps that make them up.
export function stepsOfFinding(finding: Finding, steps: SessionStep[], context: ContextPoint[]): Set<string> {
  if (finding.stepIds.length > 0) return new Set(finding.stepIds);
  if (finding.key === 'hooks') return new Set(steps.filter((step) => step.kind === 'hook').map((step) => step.id));
  if (finding.key === 'context') {
    const peak = context.reduce<ContextPoint | null>((best, point) => (best === null || point.context > best.context ? point : best), null);
    return new Set(peak === null ? [] : [peak.step.id]);
  }
  return new Set();
}

export function useWidth(box: RefObject<HTMLElement | null>, fallback = 900) {
  const [width, setWidth] = useState(fallback);

  useEffect(() => {
    const element = box.current;
    if (element === null) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, [box]);

  return width;
}

export const settings = {
  prompts: 'OTEL_LOG_USER_PROMPTS=1',
  responses: 'OTEL_LOG_ASSISTANT_RESPONSES=1',
  toolContent: 'OTEL_LOG_TOOL_CONTENT=1',
};
