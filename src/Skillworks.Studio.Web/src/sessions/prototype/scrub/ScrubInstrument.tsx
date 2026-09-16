// PROTOTYPE — throwaway. The Scrub instrument: the whole session as an overview strip with a brush, and the lanes for
// the stretch the brush holds. The cursor is shared with the Context tab, so one model call lines up in both.

import { useMemo, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import { describe, foldScale, format, lanes, lanesOf, startOf, ticks, type Activation, type FoldScale, type Lane } from '../sessionMeasures';
import type { useTip } from '../SessionTip';
import { clamp, useSize, windowAround, type Range } from './scrubRange';

type Tip = Pick<ReturnType<typeof useTip>, 'show' | 'hide'>;

const left = 112;
const right = 14;
const overviewHeight = 44;
const top = 6;
const axis = 26;
const gap = 3;

interface Mark {
  lane: Lane;
  x1: number;
  x2: number;
  step: SessionStep;
}

interface Hover {
  kind: 'step' | 'prompt' | 'activation';
  step: SessionStep;
  x1: number;
  x2: number;
  lane: number;
  activation?: Activation;
  promptIndex?: number;
}

const laneIndex = Object.fromEntries(lanes.map((lane, index) => [lane.key, index])) as Record<Lane, number>;

function markClass(mark: Mark) {
  const step = mark.step;
  if (mark.lane === 'fault') {
    return step.kind === 'rejected' || step.kind === 'hook' || (step.kind === 'tool' && step.errorType === 'HookBlocked') ? 'is-warned' : 'is-failed';
  }
  if (step.kind === 'model') return step.thread === 'main' ? 'is-main' : step.thread === 'subagent' ? 'is-sub' : 'is-side';
  if (step.kind === 'subagent') return 'is-agent';
  if (step.kind === 'hook') return 'is-hook';
  if (step.kind === 'tool') return step.ok ? 'is-tool' : 'is-tool-failed';
  return 'is-tool';
}

const diamond = (x: number, y: number, k: number) => `M${x} ${y - k}L${x + k} ${y}L${x} ${y + k}L${x - k} ${y}Z`;

function Overview({
  session,
  width,
  range,
  cursor,
  onRange,
}: {
  session: Session;
  width: number;
  range: Range | null;
  cursor: number | null;
  onRange: (range: Range | null) => void;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ mode: 'new' | 'move' | 'left' | 'right'; x: number; px: [number, number]; moved: boolean } | null>(null);

  const scale = useMemo(() => foldScale(session.steps.map((step) => [startOf(step), step.at]), left, Math.max(left + 10, width - right)), [session, width]);

  const strip = useMemo(
    () =>
      session.steps.flatMap((step) => {
        const x = scale.map(startOf(step));
        const w = Math.max(1, scale.map(step.at) - x);
        if (step.kind === 'model') return [<rect key={step.id} x={x} y={step.thread === 'main' ? 8 : 16} width={w} height={6} className={step.thread === 'main' ? 'is-main' : 'is-sub'} />];
        if (step.kind === 'tool' && !step.ok) return [<rect key={step.id} x={x} y={32} width={Math.max(2, w)} height={6} className="is-failed" />];
        if (step.kind === 'modelError') return [<rect key={step.id} x={x} y={32} width={2} height={6} className="is-failed" />];
        if (step.kind === 'tool' || step.kind === 'subagent') return [<rect key={step.id} x={x} y={24} width={w} height={6} className="is-tool" />];
        return [];
      }),
    [session, scale],
  );

  const clampMs = (ms: number) => clamp(ms, session.startMs, session.endMs);
  const toRange = (a: number, b: number): Range => {
    const low = clamp(Math.min(a, b), left, width - right);
    const high = clamp(Math.max(a, b), left, width - right);
    return [clampMs(scale.invert(low)), clampMs(scale.invert(high))];
  };
  const brush: [number, number] | null = range === null ? null : [scale.map(range[0]), scale.map(range[1])];
  const localX = (event: ReactPointerEvent) => event.clientX - (svg.current?.getBoundingClientRect().left ?? 0);

  const down = (event: ReactPointerEvent<SVGSVGElement>) => {
    const x = localX(event);
    if (x < left - 6) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    let mode: 'new' | 'move' | 'left' | 'right' = 'new';
    if (brush !== null) {
      if (Math.abs(x - brush[0]) <= 7) mode = 'left';
      else if (Math.abs(x - brush[1]) <= 7) mode = 'right';
      else if (x > brush[0] && x < brush[1]) mode = 'move';
    }
    drag.current = { mode, x, px: brush ?? [x, x], moved: false };
  };

  const move = (event: ReactPointerEvent<SVGSVGElement>) => {
    const state = drag.current;
    if (state === null) return;
    const x = localX(event);
    const dx = x - state.x;
    if (Math.abs(dx) > 3) state.moved = true;
    if (!state.moved) return;
    if (state.mode === 'new') onRange(toRange(state.x, x));
    else if (state.mode === 'left') onRange(toRange(state.px[0] + dx, state.px[1]));
    else if (state.mode === 'right') onRange(toRange(state.px[0], state.px[1] + dx));
    else {
      const span = state.px[1] - state.px[0];
      const start = clamp(state.px[0] + dx, left, width - right - span);
      onRange(toRange(start, start + span));
    }
  };

  const up = () => {
    const state = drag.current;
    drag.current = null;
    // A plain click outside the brush moves the window there, keeping its width.
    if (state !== null && !state.moved && state.mode === 'new') {
      const span = brush !== null ? brush[1] - brush[0] : Math.max(40, (width - left - right) * 0.12);
      const start = clamp(state.x - span / 2, left, width - right - span);
      onRange(toRange(start, start + span));
    }
  };

  const wall = session.endMs - session.startMs;

  return (
    <svg
      ref={svg}
      className="scrub-overview"
      width={width}
      height={overviewHeight}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onDoubleClick={() => onRange(null)}
      role="slider"
      aria-label="Brush over the whole session. Drag to choose a stretch, double-click to see it all."
      aria-valuetext={range === null ? 'Whole session' : `${format.clock(range[0], true)} to ${format.clock(range[1], true)}`}
    >
      <text x={left - 10} y={17} textAnchor="end" className="scrub-lane-label">
        Whole session
      </text>
      <text x={left - 10} y={31} textAnchor="end" className="scrub-axis">
        {format.duration(wall)}
      </text>
      <rect x={left} y={4} width={Math.max(0, width - left - right)} height={overviewHeight - 8} className="scrub-overview-ground" />
      {session.prompts.map((span) => (
        <rect key={span.index} x={scale.map(span.startMs)} y={4} width={Math.max(1, scale.map(span.endMs) - scale.map(span.startMs))} height={overviewHeight - 8} className="scrub-overview-prompt" />
      ))}
      {scale.gaps.map((fold) => (
        <line key={fold.x} x1={fold.x} x2={fold.x} y1={4} y2={overviewHeight - 4} className="scrub-fold" />
      ))}
      {strip}
      {brush !== null && (
        <>
          <rect x={left} y={2} width={Math.max(0, brush[0] - left)} height={overviewHeight - 4} className="scrub-brush-shade" />
          <rect x={brush[1]} y={2} width={Math.max(0, width - right - brush[1])} height={overviewHeight - 4} className="scrub-brush-shade" />
          <rect x={brush[0]} y={2} width={Math.max(2, brush[1] - brush[0])} height={overviewHeight - 4} className="scrub-brush" />
          <rect x={brush[0] - 3} y={overviewHeight / 2 - 9} width={6} height={18} rx={2} className="scrub-brush-handle" />
          <rect x={brush[1] - 3} y={overviewHeight / 2 - 9} width={6} height={18} rx={2} className="scrub-brush-handle" />
        </>
      )}
      {cursor !== null && <line x1={scale.map(cursor)} x2={scale.map(cursor)} y1={2} y2={overviewHeight - 2} className="scrub-cursor" />}
    </svg>
  );
}

export function ScrubInstrument({
  session,
  activations,
  range,
  cursor,
  selected,
  tip,
  onRange,
  onCursor,
  onSelect,
  onActivation,
}: {
  session: Session;
  activations: Activation[];
  range: Range | null;
  cursor: number | null;
  selected: string | null;
  tip: Tip;
  onRange: (range: Range | null) => void;
  onCursor: (ms: number | null) => void;
  onSelect: (step: SessionStep) => void;
  onActivation: (index: number) => void;
}) {
  const [frame, size] = useSize<HTMLDivElement>();
  const [hover, setHover] = useState<Hover | null>(null);
  const width = Math.max(320, size.width);
  const height = Math.max(160, size.height);
  const [from, to] = range ?? [session.startMs, session.endMs];

  const laneHeight = clamp(Math.floor((height - top - axis) / lanes.length) - gap, 9, 26);
  const laneY = (index: number) => top + index * (laneHeight + gap);
  const axisY = laneY(lanes.length) + 1;

  const scale: FoldScale = useMemo(() => {
    const intervals: [number, number][] = [
      [from, from],
      [to, to],
    ];
    for (const step of session.steps) {
      if (step.at < from || startOf(step) > to) continue;
      intervals.push([Math.max(from, startOf(step)), Math.min(to, step.at)]);
    }
    return foldScale(intervals, left, width - right);
  }, [session, from, to, width]);

  const marks = useMemo(() => {
    const byLane = new Map<Lane, Mark[]>(lanes.map((lane) => [lane.key, []]));
    for (const step of session.steps) {
      if (step.kind === 'prompt' || step.kind === 'skill' || step.at < from || startOf(step) > to) continue;
      const x1 = scale.map(Math.max(from, startOf(step)));
      const x2 = scale.map(Math.min(to, step.at));
      for (const lane of lanesOf(step)) byLane.get(lane)?.push({ lane, x1, x2: Math.max(x1, x2), step });
    }
    return byLane;
  }, [session, scale, from, to]);

  const promptsInView = session.prompts.filter((span) => span.endMs >= from && span.startMs <= to);
  const promptSteps = session.steps.filter((step) => step.kind === 'prompt' && step.at >= from && step.at <= to);
  const activationsInView = activations.filter((activation) => activation.endMs >= from && activation.startMs <= to);

  const drawn = useMemo(() => {
    const out: ReactNode[] = [];
    for (const lane of lanes) {
      const index = laneIndex[lane.key];
      const y = top + index * (laneHeight + gap);
      for (const mark of marks.get(lane.key) ?? []) {
        const className = markClass(mark);
        if (lane.key === 'fault') {
          out.push(<path key={`${lane.key}${mark.step.id}`} d={diamond(mark.x2, y + laneHeight / 2, Math.min(5, laneHeight / 2))} className={`scrub-mark ${className}`} />);
          continue;
        }
        const pad = mark.step.kind === 'subagent' ? 1 : Math.max(1, Math.round(laneHeight * 0.18));
        if (mark.step.kind === 'tool' && mark.step.waitedMs > 0) {
          const waitEnd = Math.min(mark.x2, scale.map(Math.min(to, startOf(mark.step) + mark.step.waitedMs)));
          out.push(<rect key={`w${mark.step.id}`} x={mark.x1} y={y + pad} width={Math.max(1.5, waitEnd - mark.x1)} height={laneHeight - pad * 2} className="scrub-mark is-wait" />);
          out.push(<rect key={`${lane.key}${mark.step.id}`} x={waitEnd} y={y + pad} width={Math.max(1.5, mark.x2 - waitEnd)} height={laneHeight - pad * 2} rx={1} className={`scrub-mark ${className}`} />);
          continue;
        }
        out.push(<rect key={`${lane.key}${mark.step.id}`} x={mark.x1} y={y + pad} width={Math.max(1.5, mark.x2 - mark.x1)} height={laneHeight - pad * 2} rx={1} className={`scrub-mark ${className}`} />);
      }
    }
    return out;
  }, [marks, laneHeight, scale, to]);

  const hitTest = (x: number, y: number): Hover | null => {
    const index = Math.floor((y - top) / (laneHeight + gap));
    if (index < 0 || index >= lanes.length || x < left - 4) return null;
    const lane = lanes[index].key;

    if (lane === 'prompt') {
      const onMark = promptSteps.find((step) => Math.abs(scale.map(step.at) - x) <= 6);
      if (onMark) return { kind: 'step', step: onMark, x1: scale.map(onMark.at) - 4, x2: scale.map(onMark.at) + 4, lane: index };
      const span = promptsInView.find((each) => x >= scale.map(Math.max(from, each.startMs)) - 2 && x <= scale.map(Math.min(to, each.endMs)) + 2);
      const step = span === undefined ? undefined : session.steps.find((each) => each.id === span.stepId);
      return span && step ? { kind: 'prompt', step, promptIndex: span.index, x1: scale.map(Math.max(from, span.startMs)), x2: scale.map(Math.min(to, span.endMs)), lane: index } : null;
    }

    if (lane === 'skill') {
      let best: Activation | undefined;
      for (const activation of activationsInView) {
        const x1 = scale.map(Math.max(from, activation.startMs));
        const x2 = scale.map(Math.min(to, activation.endMs));
        if (Math.abs(x - scale.map(activation.startMs)) <= 6) {
          best = activation;
          break;
        }
        if (x >= x1 && x <= x2) best = activation;
      }
      return best ? { kind: 'activation', step: best.step, activation: best, x1: scale.map(Math.max(from, best.startMs)), x2: scale.map(Math.min(to, best.endMs)), lane: index } : null;
    }

    let found: Mark | null = null;
    let distance = Infinity;
    for (const mark of marks.get(lane) ?? []) {
      const reach = lane === 'fault' ? 7 : 5;
      if (x < mark.x1 - reach || x > mark.x2 + reach) continue;
      const centre = lane === 'fault' ? mark.x2 : (mark.x1 + mark.x2) / 2;
      // Inside a wide bar every point is a hit; the narrowest candidate wins, so a short step beside a long one stays reachable.
      const score = Math.abs(x - centre) + (mark.x2 - mark.x1) * 0.01;
      if (score < distance) {
        distance = score;
        found = mark;
      }
    }
    return found === null ? null : { kind: 'step', step: found.step, x1: lane === 'fault' ? found.x2 - 5 : found.x1, x2: lane === 'fault' ? found.x2 + 5 : found.x2, lane: index };
  };

  const pointer = (event: ReactPointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - box.left;
    const y = event.clientY - box.top;
    onCursor(x >= left && x <= width - right ? clamp(scale.invert(x), from, to) : null);
    const hit = hitTest(x, y);
    setHover(hit);
    if (hit === null) {
      tip.hide();
      return;
    }
    const hint = hit.kind === 'prompt' ? 'Click to brush this prompt' : hit.kind === 'activation' ? 'Click to brush this skill call' : 'Click for the trace';
    tip.show(describe(hit.step, session), event, hint);
  };

  const click = () => {
    if (hover === null) return;
    if (hover.kind === 'prompt' && hover.promptIndex !== undefined) {
      const span = session.prompts[hover.promptIndex];
      onRange(windowAround(span.startMs, span.endMs, session));
    } else if (hover.kind === 'activation' && hover.activation) {
      onActivation(hover.activation.index);
    } else {
      onSelect(hover.step);
    }
  };

  const selectedMarks = selected === null ? [] : [...marks.values()].flat().filter((mark) => mark.step.id === selected);
  const selectedPrompt = selected === null ? undefined : promptSteps.find((step) => step.id === selected);
  const cursorX = cursor !== null && cursor >= from && cursor <= to ? scale.map(cursor) : null;
  const tickMarks = ticks(scale, 70);

  return (
    <section className="scrub-instrument" aria-label="Timeline">
      <div className="scrub-instrument-head">
        <span className="scrub-micro">Timeline</span>
        <span className="scrub-range-readout">
          {range === null ? 'Whole session' : `In view ${format.clock(from, true)} – ${format.clock(to, true)} · ${format.duration(to - from)}`}
        </span>
        {range !== null && (
          <button type="button" className="scrub-small-button" onClick={() => onRange(null)}>
            Whole session
          </button>
        )}
        <span className="scrub-hint">Drag the strip to brush · double-click to reset · folds hide idle over 3 min</span>
        <span className="scrub-legend" aria-label="Legend">
          <span><i className="scrub-sw-main" />Main model</span>
          <span><i className="scrub-sw-sub" />Subagent or side model</span>
          <span><i className="scrub-sw-agent" />Subagent at work</span>
          <span><i className="scrub-sw-tool" />Tool</span>
          <span><i className="scrub-sw-wait" />Waiting for OK</span>
          <span><i className="scrub-sw-hook" />Hook</span>
          <span><i className="scrub-sw-fail" />Failed</span>
        </span>
      </div>

      <Overview session={session} width={width} range={range} cursor={cursor} onRange={onRange} />

      <div className="scrub-lanes" ref={frame}>
        <svg
          width={width}
          height={height}
          className={`scrub-detail${hover !== null ? ' is-pointing' : ''}`}
          onPointerMove={pointer}
          onPointerLeave={() => {
            onCursor(null);
            setHover(null);
            tip.hide();
          }}
          onClick={click}
          role="img"
          aria-label="Lanes for the stretch in view"
        >
          {lanes.map((lane, index) => (
            <g key={lane.key}>
              <text x={left - 10} y={laneY(index) + laneHeight / 2 + 3.5} textAnchor="end" className={`scrub-lane-label${lane.key === 'fault' ? ' is-fault' : ''}`}>
                {lane.label}
              </text>
              <line x1={left} x2={width - right} y1={laneY(index) + laneHeight / 2} y2={laneY(index) + laneHeight / 2} className="scrub-track" />
            </g>
          ))}

          {tickMarks.map((tick) => (
            <g key={tick.ms}>
              <line x1={tick.x} x2={tick.x} y1={top} y2={axisY} className="scrub-grid" />
              <text x={tick.x} y={axisY + 14} textAnchor="middle" className="scrub-axis">
                {tick.label}
              </text>
            </g>
          ))}

          {scale.gaps.map((fold) => (
            <g key={fold.x}>
              <line x1={fold.x} x2={fold.x} y1={top} y2={axisY} className="scrub-fold" />
              {fold.toMs - fold.fromMs > 0 && (
                <text x={fold.x} y={axisY + 24} textAnchor="middle" className="scrub-fold-label">
                  {format.short(fold.toMs - fold.fromMs)}
                </text>
              )}
            </g>
          ))}

          {promptsInView.map((span) => {
            const x1 = scale.map(Math.max(from, span.startMs));
            const x2 = scale.map(Math.min(to, span.endMs));
            const y = laneY(laneIndex.prompt);
            return (
              <g key={span.index}>
                <rect x={x1} y={y + 1} width={Math.max(3, x2 - x1)} height={laneHeight - 2} className="scrub-prompt-band" />
                {x2 - x1 > 28 && (
                  <text x={x1 + 10} y={y + laneHeight / 2 + 3.5} className="scrub-band-label">
                    P{span.index + 1}
                  </text>
                )}
              </g>
            );
          })}
          {promptSteps.map((step) => {
            const x = scale.map(step.at);
            const y = laneY(laneIndex.prompt);
            return <path key={step.id} d={`M${x - 4} ${y}H${x + 4}L${x} ${y + Math.min(8, laneHeight - 2)}Z`} className="scrub-prompt-mark" />;
          })}

          {activationsInView.map((activation) => {
            const x1 = scale.map(Math.max(from, activation.startMs));
            const x2 = scale.map(Math.min(to, activation.endMs));
            const y = laneY(laneIndex.skill);
            const flagged = activation.startMs >= from;
            const fits = x2 - x1 > activation.step.skill.length * 6 + 18;
            return (
              <g key={activation.index}>
                <rect x={x1} y={y + laneHeight * 0.3} width={Math.max(1, x2 - x1)} height={laneHeight * 0.4} className="scrub-skill-band" />
                {flagged && <path d={`M${x1} ${y + laneHeight}V${y}L${x1 + 7} ${y + 3.5}L${x1} ${y + 7}`} className="scrub-skill-flag" />}
                {fits && (
                  <text x={x1 + 10} y={y + laneHeight / 2 + 3.5} className="scrub-band-label">
                    {activation.step.skill}
                  </text>
                )}
              </g>
            );
          })}

          {drawn}

          {selectedMarks.map((mark) => {
            const x1 = mark.lane === 'fault' ? mark.x2 - 6 : mark.x1 - 3;
            const x2 = mark.lane === 'fault' ? mark.x2 + 6 : mark.x2 + 3;
            return <rect key={`sel${mark.lane}`} x={x1} y={laneY(laneIndex[mark.lane]) - 2} width={Math.max(6, x2 - x1)} height={laneHeight + 4} className="scrub-selected" />;
          })}
          {selectedPrompt && <rect x={scale.map(selectedPrompt.at) - 6} y={laneY(0) - 2} width={12} height={laneHeight + 4} className="scrub-selected" />}

          {hover !== null && <rect x={hover.x1 - 2} y={laneY(hover.lane) - 1} width={Math.max(4, hover.x2 - hover.x1 + 4)} height={laneHeight + 2} className="scrub-hovered" />}

          {cursorX !== null && cursor !== null && (
            <g className="scrub-crosshair">
              <line x1={cursorX} x2={cursorX} y1={top} y2={axisY} className="scrub-cursor" />
              <rect x={clamp(cursorX - 34, left, width - right - 68)} y={axisY + 2} width={68} height={16} className="scrub-cursor-box" />
              <text x={clamp(cursorX, left + 34, width - right - 34)} y={axisY + 14} textAnchor="middle" className="scrub-cursor-text">
                {format.clock(cursor, true)}
              </text>
            </g>
          )}
        </svg>
      </div>
    </section>
  );
}
