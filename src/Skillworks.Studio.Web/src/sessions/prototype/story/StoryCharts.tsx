// PROTOTYPE — throwaway. The two small charts under the minimap: where the time went, and context on each main call.

import { memo, useMemo, useState, type MouseEvent } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import { describe, format, type Activation, type ContextPoint, type Description, type TimeKind, type TimePart } from '../sessionMeasures';
import { useStoryBox } from './useStoryBox';

type ShowTip = (description: Description, event: { clientX: number; clientY: number }, hint?: string | null) => void;

export const TimeBars = memo(function TimeBars({ split, wallMs }: { split: { parts: TimePart[]; kinds: TimeKind[] }; wallMs: number }) {
  const parts = split.parts.filter((part) => part.ms > 0);
  // Kinds overlap, so three subagents at once can add up to more than the session; the scale grows to hold them.
  const kindScale = Math.max(wallMs, ...split.kinds.map((kind) => kind.ms), 1);

  return (
    <section className="story-block" aria-label="Where the time went">
      <p className="story-block-title">
        <span>Where the time went</span>
        <span className="story-fig">{format.duration(wallMs)}</span>
      </p>
      <p className="story-quiet">Each moment counted once, so these add up to the length.</p>
      <dl className="story-bars">
        {parts.map((part) => (
          <div key={part.key} className="story-bar" title={part.note}>
            <dt>{part.label}</dt>
            <dd className="story-bar-track">
              <i className={`is-${part.key}`} style={{ width: `${(part.ms / Math.max(1, wallMs)) * 100}%` }} />
            </dd>
            <dd className="story-fig">{format.short(part.ms)}</dd>
          </div>
        ))}
      </dl>
      <p className="story-quiet story-bars-split">Added up by kind. Work in parallel overlaps.</p>
      <dl className="story-bars">
        {split.kinds.map((kind) => (
          <div key={kind.key} className="story-bar">
            <dt>{kind.label}</dt>
            <dd className="story-bar-track">
              <i className="is-kind" style={{ width: `${(kind.ms / kindScale) * 100}%` }} />
            </dd>
            <dd className="story-fig">{format.short(kind.ms)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
});

const niceMax = (value: number) => {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  return ([1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].find((step) => step * power >= value) ?? 10) * power;
};

export const ContextCharts = memo(function ContextCharts({
  session,
  points,
  acts,
  focusStepId,
  onOpen,
  showTip,
  hideTip,
}: {
  session: Session;
  points: ContextPoint[];
  acts: Activation[];
  focusStepId: string | null;
  onOpen: (step: SessionStep) => void;
  showTip: ShowTip;
  hideTip: () => void;
}) {
  const [ref, box] = useStoryBox<HTMLDivElement>(290, 200);
  const [hover, setHover] = useState<number | null>(null);
  const width = Math.max(220, box.width);
  const left = 34;
  const right = width - 6;
  const top = 16;
  const contextHeight = 104;
  const contextBase = top + contextHeight;
  const costTop = contextBase + 30;
  const costHeight = 40;
  const costBase = costTop + costHeight;
  const height = costBase + 16;

  const shape = useMemo(() => {
    const count = Math.max(1, points.length);
    const stepWidth = count > 1 ? (right - left) / (count - 1) : right - left;
    const x = (index: number) => (count > 1 ? left + index * stepWidth : (left + right) / 2);
    const maxContext = niceMax(Math.max(...points.map((point) => point.context), 1));
    const maxCost = niceMax(Math.max(...points.map((point) => point.step.costUsd), 0.001));
    const y = (value: number) => contextBase - (value / maxContext) * contextHeight;

    const bands: { skill: string; from: number; to: number }[] = [];
    for (const point of points) {
      const skill = point.step.skill;
      const last = bands[bands.length - 1];
      if (skill === null) continue;
      if (last !== undefined && last.skill === skill && last.to === point.index - 1) last.to = point.index;
      else bands.push({ skill, from: point.index, to: point.index });
    }

    // An activation lands on the first main call after it fired.
    const fired = acts
      .map((act) => ({ act, index: points.findIndex((point) => point.step.at - point.step.ms >= act.startMs) }))
      .filter((each) => each.index >= 0);

    const line = points.map((point) => `${x(point.index).toFixed(1)},${y(point.context).toFixed(1)}`).join('L');
    return { stepWidth, x, y, maxContext, maxCost, bands, fired, line };
  }, [points, acts, left, right, contextBase]);

  if (points.length < 2) {
    return (
      <section className="story-block" aria-label="Context on each model call">
        <p className="story-block-title">
          <span>Context on each call</span>
        </p>
        <p className="story-quiet">Fewer than two main-thread model calls in this session.</p>
      </section>
    );
  }

  const indexAt = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return Math.max(0, Math.min(points.length - 1, Math.round((event.clientX - rect.left - left) / shape.stepWidth)));
  };

  const hovered = hover === null ? null : points[hover];
  const focusIndex = points.findIndex((point) => point.step.id === focusStepId);
  const barWidth = Math.max(1, Math.min(8, shape.stepWidth - 1.5));

  return (
    <section className="story-block" aria-label="Context on each model call">
      <p className="story-block-title">
        <span>Context on each main call</span>
        <span className="story-faint">of {format.tokens(session.contextLimit)}</span>
      </p>
      <div ref={ref} className="story-context">
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Context tokens and cost on each main-thread model call, with the skill in force behind"
          className="is-pointing"
          onPointerMove={(event) => {
            const index = indexAt(event);
            setHover(index);
            const point = points[index];
            const description = describe(point.step, session);
            showTip(
              { ...description, title: `Call ${index + 1} of ${points.length} · ${description.title}`, rows: point.rebuilt ? [...description.rows, ['Cache', 'rebuilt on this call']] : description.rows },
              event,
            );
          }}
          onPointerLeave={() => {
            setHover(null);
            hideTip();
          }}
          onClick={(event) => onOpen(points[indexAt(event)].step)}
        >
          {shape.bands.map((band, index) => {
            const x1 = shape.x(band.from) - shape.stepWidth / 2;
            const x2 = shape.x(band.to) + shape.stepWidth / 2;
            const room = x2 - x1;
            return (
              <g key={`${band.skill}${band.from}`}>
                <rect x={Math.max(left, x1)} y={top} width={Math.max(1, Math.min(right, x2) - Math.max(left, x1))} height={contextHeight} className={`story-band${index % 2 ? ' is-alt' : ''}`} />
                {room > band.skill.length * 5.4 + 4 && (
                  <text x={Math.max(left, x1) + 3} y={top + 10} className="story-svg-faint">
                    {band.skill}
                  </text>
                )}
              </g>
            );
          })}

          {[0, shape.maxContext / 2, shape.maxContext].map((value) => (
            <g key={value}>
              <line x1={left} x2={right} y1={shape.y(value)} y2={shape.y(value)} className="story-gridline" />
              <text x={left - 4} y={shape.y(value) + 3} textAnchor="end" className="story-svg-axis">
                {format.tokens(value)}
              </text>
            </g>
          ))}

          {shape.fired.map(({ act, index }) => (
            <g key={act.index}>
              <line x1={shape.x(index)} x2={shape.x(index)} y1={top - 4} y2={contextBase} className="story-fired" />
              <path d={`M${shape.x(index)} ${top - 4}l5 3l-5 3z`} className="story-mark is-skill" />
            </g>
          ))}

          <path d={`M${shape.x(0)},${contextBase}L${shape.line}L${shape.x(points.length - 1)},${contextBase}Z`} className="story-area" />
          <path d={`M${shape.line}`} className="story-line" />
          {points
            .filter((point) => point.rebuilt)
            .map((point) => (
              <circle key={point.step.id} cx={shape.x(point.index)} cy={shape.y(point.context)} r={3.5} className="story-ring" />
            ))}

          <text x={left} y={costTop - 6} className="story-svg-label">
            Cost per call
          </text>
          <line x1={left} x2={right} y1={costBase} y2={costBase} className="story-gridline" />
          <text x={left - 4} y={costTop + 4} textAnchor="end" className="story-svg-axis">
            {format.usd(shape.maxCost)}
          </text>
          {points.map((point) => {
            const barHeight = Math.max(0.5, (point.step.costUsd / shape.maxCost) * costHeight);
            return <rect key={point.step.id} x={shape.x(point.index) - barWidth / 2} y={costBase - barHeight} width={barWidth} height={barHeight} className={`story-cost${point.index === hover ? ' is-on' : ''}`} />;
          })}
          <text x={left} y={costBase + 12} className="story-svg-axis">
            call 1
          </text>
          <text x={right} y={costBase + 12} textAnchor="end" className="story-svg-axis">
            call {points.length}
          </text>

          {focusIndex >= 0 && <circle cx={shape.x(focusIndex)} cy={shape.y(points[focusIndex].context)} r={5} className="story-focus-ring" />}

          {hovered !== null && (
            <g className="story-cross">
              <line x1={shape.x(hovered.index)} x2={shape.x(hovered.index)} y1={top} y2={costBase} />
              <circle cx={shape.x(hovered.index)} cy={shape.y(hovered.context)} r={4} />
            </g>
          )}
        </svg>
      </div>
      <p className="story-legend">
        <span>
          <i className="is-line" />
          context tokens
        </span>
        <span>
          <i className="is-band" />
          skill in force
        </span>
        <span>
          <i className="is-skill-flag" />
          skill fired
        </span>
        <span>
          <i className="is-ring" />
          cache rebuilt
        </span>
        <span>
          <i className="is-tool" />
          cost
        </span>
      </p>
    </section>
  );
});
