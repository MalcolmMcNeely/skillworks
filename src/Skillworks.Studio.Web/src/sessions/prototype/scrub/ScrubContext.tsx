// PROTOTYPE — throwaway. The Context tab: tokens sent on each main-thread model call in view, with the skill in force
// behind each call, and cost per call as its own chart on the same calls. Its cursor is the instrument's cursor.

import { useMemo, type PointerEvent as ReactPointerEvent } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import { describe, format, type Activation, type ContextPoint } from '../sessionMeasures';
import type { useTip } from '../SessionTip';
import { niceMax, overlaps, useSize, type Range } from './scrubRange';

type Tip = Pick<ReturnType<typeof useTip>, 'show' | 'hide'>;

export function ScrubContext({
  session,
  points,
  activations,
  range,
  cursor,
  selected,
  tip,
  onCursor,
  onSelect,
}: {
  session: Session;
  points: ContextPoint[];
  activations: Activation[];
  range: Range | null;
  cursor: number | null;
  selected: string | null;
  tip: Tip;
  onCursor: (ms: number | null) => void;
  onSelect: (step: SessionStep) => void;
}) {
  const [frame, size] = useSize<HTMLDivElement>();
  const shown = useMemo(() => points.filter((point) => overlaps(point.step.at - point.step.ms, point.step.at, range)), [points, range]);

  const width = Math.max(320, size.width);
  const height = Math.max(200, size.height);
  const left = 56;
  const right = 18;
  const top = 22;
  const costHeight = Math.max(40, Math.round(height * 0.2));
  const gap = 34;
  const contextHeight = height - top - gap - costHeight - 22;
  const costBase = top + contextHeight + gap + costHeight;

  if (shown.length === 0) {
    return (
      <div className="scrub-context">
        <div className="scrub-context-plot" ref={frame}>
          <div className="scrub-dock-empty">
            <p>No main-thread model call in view.</p>
            <p className="scrub-quiet">Brush a wider stretch of the timeline.</p>
          </div>
        </div>
      </div>
    );
  }

  const count = shown.length;
  const stepX = count > 1 ? (width - left - right) / (count - 1) : 0;
  const x = (index: number) => (count > 1 ? left + index * stepX : left + (width - left - right) / 2);
  const contextMax = niceMax(Math.max(...shown.map((point) => point.context)));
  const costMax = niceMax(Math.max(...shown.map((point) => point.step.costUsd)));
  const y = (value: number) => top + contextHeight - (value / contextMax) * contextHeight;
  const half = Math.max(2, stepX / 2);

  const bands: { skill: string; from: number; to: number }[] = [];
  shown.forEach((point, index) => {
    const skill = point.step.skill;
    const last = bands[bands.length - 1];
    if (skill === null) return;
    if (last && last.skill === skill && last.to === index - 1) last.to = index;
    else bands.push({ skill, from: index, to: index });
  });

  const ticksAt = activations
    .filter((activation) => overlaps(activation.startMs, activation.startMs, range))
    .map((activation) => {
      const after = shown.findIndex((point) => point.step.at - point.step.ms >= activation.startMs);
      return { activation, x: after < 0 ? x(count - 1) + half : after === 0 ? x(0) - half : x(after) - half };
    })
    .filter((tick) => tick.x >= left - half - 1 && tick.x <= width - right + half + 1);

  const line = shown.map((point, index) => `${x(index).toFixed(1)},${y(point.context).toFixed(1)}`).join('L');
  const barWidth = Math.max(1.5, Math.min(10, stepX - 2));

  let cursorIndex: number | null = null;
  const first = shown[0].step;
  const last = shown[count - 1].step;
  // Only a cursor over the calls in view; one far off in an idle fold would pin the crosshair to an edge.
  if (cursor !== null && cursor >= first.at - first.ms - 60_000 && cursor <= last.at + 60_000) {
    let best = Infinity;
    for (let index = 0; index < count; index += 1) {
      const distance = Math.abs(shown[index].step.at - cursor);
      if (distance < best) {
        best = distance;
        cursorIndex = index;
      }
    }
  }

  const pointer = (event: ReactPointerEvent<SVGRectElement>) => {
    const box = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (!box) return;
    const index = count > 1 ? Math.max(0, Math.min(count - 1, Math.round((event.clientX - box.left - left) / stepX))) : 0;
    const point = shown[index];
    onCursor(point.step.at);
    const description = describe(point.step, session);
    tip.show(
      {
        ...description,
        title: `Call ${point.index + 1} · ${description.title}`,
        rows: [...description.rows, ...(point.rebuilt ? ([['Cache', 'rebuilt on this call']] as [string, string][]) : []), ...(point.compacted ? ([['Compaction', 'just before this call']] as [string, string][]) : [])],
      },
      event,
    );
  };

  const selectedIndex = shown.findIndex((point) => point.step.id === selected);
  const limitShare = shown.reduce((peak, point) => Math.max(peak, point.share), 0);

  return (
    <div className="scrub-context">
      <div className="scrub-context-plot" ref={frame}>
      <svg width={width} height={height} role="img" aria-label="Context tokens and cost on each main-thread model call in view">
        <text x={left} y={12} className="scrub-lane-label">
          Context tokens per main-thread call · peak {format.percent(limitShare)} of the {format.tokens(session.contextLimit)} limit
        </text>

        {bands.map((band, index) => {
          const x1 = x(band.from) - half;
          const x2 = x(band.to) + half;
          const fits = x2 - x1 > band.skill.length * 6.2 + 10;
          return (
            <g key={`${band.skill}${band.from}`}>
              <rect x={Math.max(left - half, x1)} y={top} width={Math.max(1, x2 - x1)} height={contextHeight} className={`scrub-skill-zone${index % 2 ? ' is-alt' : ''}`} />
              {fits && (
                <text x={x1 + 5} y={top + 12} className="scrub-band-label">
                  {band.skill}
                </text>
              )}
            </g>
          );
        })}

        {[0, contextMax / 2, contextMax].map((value) => (
          <g key={value}>
            <line x1={left} x2={width - right} y1={y(value)} y2={y(value)} className="scrub-grid" />
            <text x={left - 8} y={y(value) + 3.5} textAnchor="end" className="scrub-axis">
              {format.tokens(value)}
            </text>
          </g>
        ))}

        {ticksAt.map((tick) => (
          <g key={tick.activation.index}>
            <line x1={tick.x} x2={tick.x} y1={top} y2={top + contextHeight} className="scrub-activation-tick" />
            <path d={`M${tick.x} ${top + 16}V${top}L${tick.x + 7} ${top + 3.5}L${tick.x} ${top + 7}`} className="scrub-skill-flag" />
          </g>
        ))}

        {count > 1 ? (
          <>
            <path d={`M${x(0)},${y(0)}L${line}L${x(count - 1)},${y(0)}Z`} className="scrub-context-area" />
            <path d={`M${line}`} className="scrub-context-line" />
          </>
        ) : (
          <circle cx={x(0)} cy={y(shown[0].context)} r={4} className="scrub-context-end" />
        )}
        {shown.map((point, index) =>
          point.rebuilt ? <circle key={point.step.id} cx={x(index)} cy={y(point.context)} r={4} className="scrub-context-ring" /> : null,
        )}
        {shown.map((point, index) =>
          point.compacted ? <path key={`c${point.step.id}`} d={`M${x(index)} ${y(point.context) - 6}l5 6l-5 6l-5 -6Z`} className="scrub-context-compact" /> : null,
        )}
        {count > 1 && <circle cx={x(count - 1)} cy={y(shown[count - 1].context)} r={4} className="scrub-context-end" />}

        <text x={left} y={costBase - costHeight - 10} className="scrub-lane-label">
          Cost per call
        </text>
        <line x1={left} x2={width - right} y1={costBase} y2={costBase} className="scrub-grid" />
        <text x={left - 8} y={costBase - costHeight + 3.5} textAnchor="end" className="scrub-axis">
          {format.usd(costMax)}
        </text>
        <text x={left - 8} y={costBase + 3.5} textAnchor="end" className="scrub-axis">
          $0
        </text>
        {shown.map((point, index) => {
          const barHeight = Math.max(0.5, (point.step.costUsd / costMax) * costHeight);
          return <rect key={`b${point.step.id}`} x={x(index) - barWidth / 2} y={costBase - barHeight} width={barWidth} height={barHeight} className={`scrub-cost-bar${point.rebuilt ? ' is-rebuilt' : ''}`} />;
        })}
        <text x={left} y={costBase + 16} className="scrub-axis">
          call {shown[0].index + 1} · {format.clock(shown[0].step.at)}
        </text>
        <text x={width - right} y={costBase + 16} textAnchor="end" className="scrub-axis">
          call {shown[count - 1].index + 1} · {format.clock(shown[count - 1].step.at)}
        </text>

        {selectedIndex >= 0 && <line x1={x(selectedIndex)} x2={x(selectedIndex)} y1={top} y2={costBase} className="scrub-selected-line" />}

        {cursorIndex !== null && (
          <g>
            <line x1={x(cursorIndex)} x2={x(cursorIndex)} y1={top} y2={costBase} className="scrub-cursor" />
            <circle cx={x(cursorIndex)} cy={y(shown[cursorIndex].context)} r={4.5} className="scrub-cursor-dot" />
          </g>
        )}

        <rect
          x={left - half - 4}
          y={top}
          width={width - left - right + half * 2 + 8}
          height={costBase - top}
          className="scrub-hit"
          onPointerMove={pointer}
          onPointerLeave={() => {
            onCursor(null);
            tip.hide();
          }}
          onClick={(event) => {
            const box = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
            if (!box) return;
            const index = count > 1 ? Math.max(0, Math.min(count - 1, Math.round((event.clientX - box.left - left) / stepX))) : 0;
            onSelect(shown[index].step);
          }}
        />
      </svg>
      </div>
      <p className="scrub-legend scrub-context-legend">
        <span><i className="scrub-sw-main" />Context tokens</span>
        <span><i className="scrub-sw-zone" />Skill in force</span>
        <span><i className="scrub-sw-flag" />Skill fired</span>
        <span><i className="scrub-sw-ring" />Cache rebuilt</span>
        <span><i className="scrub-sw-tool" />Cost of the call</span>
      </p>
    </div>
  );
}
