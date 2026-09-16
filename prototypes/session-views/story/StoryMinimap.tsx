// PROTOTYPE — throwaway. The whole session standing on end beside the transcript: time runs down, one thin column per
// lane, and a bracket shows which part the reader has on screen.

import { memo, useMemo, useState, type MouseEvent } from 'react';
import type { PromptStep, Session, SessionStep } from '../sessionModel';
import { describe, foldScale, format, lanes, lanesOf, sessionIntervals, startOf, ticks, type Activation, type Description, type Lane } from '../sessionMeasures';
import { useStoryBox } from './useStoryBox';

type ShowTip = (description: Description, event: { clientX: number; clientY: number }, hint?: string | null) => void;

const short: Record<Lane, string> = {
  prompt: 'Prompts',
  skill: 'Skills',
  main: 'Model',
  other: 'Other',
  subagent: 'Agents',
  shell: 'Shell',
  edit: 'Edit',
  read: 'Read',
  tool: 'Tools',
  hook: 'Hooks',
  fault: 'Faults',
};

const labelHeight = 50;
const axisWidth = 40;

const toneOf = (step: SessionStep, lane: Lane) => {
  if (lane === 'fault') return step.kind === 'rejected' || step.kind === 'hook' ? 'is-warned' : 'is-failed';
  if (step.kind === 'model') return step.thread === 'main' ? 'is-main' : 'is-other';
  if (step.kind === 'subagent') return 'is-agent';
  if (step.kind === 'hook') return 'is-hook';
  if (step.kind === 'skill') return 'is-skill';
  return 'is-tool';
};

export const StoryMinimap = memo(function StoryMinimap({
  session,
  visible,
  focusStepId,
  activation,
  onOpen,
  onJump,
  showTip,
  hideTip,
}: {
  session: Session;
  visible: [number, number] | null;
  focusStepId: string | null;
  activation: Activation | null;
  onOpen: (step: SessionStep) => void;
  onJump: (ms: number) => void;
  showTip: ShowTip;
  hideTip: () => void;
}) {
  const [ref, box] = useStoryBox<HTMLDivElement>(300, 420);
  const [pointer, setPointer] = useState<{ y: number; ms: number; pointing: boolean } | null>(null);
  const width = Math.max(220, box.width);
  const height = Math.max(240, box.height);
  const laneWidth = (width - axisWidth - 2) / lanes.length;
  const top = labelHeight + 6;
  const bottom = height - 6;

  const drawn = useMemo(() => {
    const scale = foldScale(sessionIntervals(session.steps), top, bottom);
    const byLane = new Map<Lane, { step: SessionStep; y1: number; y2: number }[]>(lanes.map((lane) => [lane.key, []]));
    for (const step of session.steps) {
      if (step.kind === 'prompt') continue;
      for (const lane of lanesOf(step)) byLane.get(lane)?.push({ step, y1: scale.map(startOf(step)), y2: scale.map(step.at) });
    }
    const prompts = session.prompts.map((span) => ({
      span,
      step: session.steps.find((step): step is PromptStep => step.id === span.stepId && step.kind === 'prompt'),
      y1: scale.map(span.startMs),
      y2: scale.map(span.endMs),
    }));
    // Clock labels first, then the length of each fold where one still fits, so no two labels print over each other.
    const clocks = ticks(scale, 26);
    const kept: { y: number; text: string; faint: boolean }[] = clocks.map((tick) => ({ y: tick.x, text: tick.label, faint: false }));
    const start = session.startMs;
    if (kept.every((label) => Math.abs(label.y - scale.map(start)) >= 12)) kept.push({ y: scale.map(start) + 4, text: format.clock(start), faint: false });
    for (const gap of scale.gaps) {
      if (kept.every((label) => Math.abs(label.y - gap.x) >= 12)) kept.push({ y: gap.x, text: `⋯${format.short(gap.toMs - gap.fromMs)}`, faint: true });
    }
    return { scale, byLane, prompts, ticks: clocks, labels: kept };
  }, [session, top, bottom]);

  const laneX = (index: number) => axisWidth + index * laneWidth;

  const find = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const ms = drawn.scale.invert(y);
    if (x < axisWidth || y < top - 2) return { y, ms, step: null as SessionStep | null, prompt: null as PromptStep | null };
    const lane = lanes[Math.min(lanes.length - 1, Math.floor((x - axisWidth) / laneWidth))].key;
    if (lane === 'prompt') {
      const hit = drawn.prompts.find((each) => y >= each.y1 - 3 && y <= each.y2 + 3);
      return { y, ms, step: null, prompt: hit?.step ?? null };
    }
    let best: SessionStep | null = null;
    let distance = 5;
    for (const mark of drawn.byLane.get(lane) ?? []) {
      const away = y < mark.y1 ? mark.y1 - y : y > Math.max(mark.y2, mark.y1 + 2) ? y - Math.max(mark.y2, mark.y1 + 2) : 0;
      if (away < distance) {
        distance = away;
        best = mark.step;
      }
    }
    return { y, ms, step: best, prompt: null };
  };

  const focus = focusStepId === null ? null : (session.steps.find((step) => step.id === focusStepId) ?? null);

  return (
    <section className="story-block story-minimap-block" aria-label="Minimap of the whole session">
      <p className="story-block-title">
        <span>The whole session</span>
        <span className="story-faint">click to go there</span>
      </p>
      <div ref={ref} className="story-minimap">
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Every step of the session, time running down"
          className={pointer?.pointing ? 'is-pointing' : undefined}
          onPointerMove={(event) => {
            const hit = find(event);
            setPointer({ y: hit.y, ms: hit.ms, pointing: hit.step !== null || hit.prompt !== null });
            if (hit.step !== null) showTip(describe(hit.step, session), event);
            else if (hit.prompt !== null) showTip(describe(hit.prompt, session), event, 'Click to read it');
            else hideTip();
          }}
          onPointerLeave={() => {
            setPointer(null);
            hideTip();
          }}
          onClick={(event) => {
            const hit = find(event);
            if (hit.step !== null) onOpen(hit.step);
            else onJump(hit.ms);
          }}
        >
          {lanes.map((lane, index) => (
            <g key={lane.key}>
              <text transform={`translate(${laneX(index) + laneWidth / 2 + 3} ${labelHeight}) rotate(-90)`} className="story-svg-label">
                {short[lane.key]}
              </text>
              <rect x={laneX(index) + laneWidth / 2 - 0.5} y={top} width={1} height={bottom - top} className="story-track" />
            </g>
          ))}

          {drawn.ticks.map((tick) => (
            <line key={tick.ms} x1={axisWidth - 3} x2={width - 2} y1={tick.x} y2={tick.x} className="story-gridline" />
          ))}

          {drawn.scale.gaps.map((gap) => (
            <line key={gap.x} x1={axisWidth - 3} x2={width - 2} y1={gap.x} y2={gap.x} className="story-gapline" />
          ))}

          {drawn.labels.map((label) => (
            <text key={`${label.y}${label.text}`} x={axisWidth - 5} y={label.y + 3} textAnchor="end" className={label.faint ? 'story-svg-faint' : 'story-svg-axis'}>
              {label.text}
            </text>
          ))}

          {activation !== null && (
            <rect x={axisWidth} y={drawn.scale.map(activation.startMs)} width={width - axisWidth - 2} height={Math.max(2, drawn.scale.map(activation.endMs) - drawn.scale.map(activation.startMs))} className="story-mini-activation" />
          )}

          {drawn.prompts.map(({ span, y1, y2 }) => (
            <rect key={span.index} x={laneX(0) + 3} y={y1} width={laneWidth - 6} height={Math.max(2, y2 - y1)} className="story-mini-prompt" />
          ))}

          {lanes.slice(1).map((lane, offset) => {
            const index = offset + 1;
            const x = laneX(index);
            return (drawn.byLane.get(lane.key) ?? []).map(({ step, y1, y2 }) =>
              lane.key === 'fault' || lane.key === 'skill' ? (
                <path
                  key={`${lane.key}${step.id}`}
                  d={lane.key === 'fault' ? `M${x + laneWidth / 2} ${y2 - 3.5}L${x + laneWidth / 2 + 3.5} ${y2}L${x + laneWidth / 2} ${y2 + 3.5}L${x + laneWidth / 2 - 3.5} ${y2}Z` : `M${x + 3} ${y2}H${x + laneWidth - 3}`}
                  className={`story-mark ${toneOf(step, lane.key)}`}
                />
              ) : (
                <rect key={`${lane.key}${step.id}`} x={x + 3} y={y1} width={laneWidth - 6} height={Math.max(1.2, y2 - y1)} className={`story-mark ${toneOf(step, lane.key)}`} />
              ),
            );
          })}

          {visible !== null && (
            <g className="story-mini-view">
              <rect x={axisWidth - 1} y={drawn.scale.map(visible[0])} width={width - axisWidth} height={Math.max(4, drawn.scale.map(visible[1]) - drawn.scale.map(visible[0]))} />
              <path d={`M${axisWidth - 1} ${drawn.scale.map(visible[0])}h-4V${Math.max(drawn.scale.map(visible[0]) + 4, drawn.scale.map(visible[1]))}h4`} />
            </g>
          )}

          {focus !== null && (
            <g className="story-mini-focus">
              <line x1={axisWidth} x2={width - 2} y1={drawn.scale.map(focus.at)} y2={drawn.scale.map(focus.at)} />
              <circle cx={axisWidth - 1} cy={drawn.scale.map(focus.at)} r={3.5} />
            </g>
          )}

          {pointer !== null && pointer.y >= top && (
            <g className="story-mini-pointer">
              <line x1={axisWidth} x2={width - 2} y1={pointer.y} y2={pointer.y} />
            </g>
          )}
        </svg>
      </div>
      <p className="story-legend">
        <span>
          <i className="is-main" />
          model, main
        </span>
        <span>
          <i className="is-other" />
          other model
        </span>
        <span>
          <i className="is-agent" />
          subagent
        </span>
        <span>
          <i className="is-tool" />
          tool
        </span>
        <span>
          <i className="is-hook" />
          hook
        </span>
        <span>
          <i className="is-failed is-diamond" />
          failed
        </span>
        <span>
          <i className="is-view" />
          on screen
        </span>
      </p>
    </section>
  );
});
