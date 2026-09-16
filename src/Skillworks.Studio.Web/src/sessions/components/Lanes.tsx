import { useMemo, type PointerEvent } from 'react';
import { holds } from '../lib/brush';
import { foldScale, ticksOf } from '../lib/fold';
import { describeClock, describeSpell, lanes, lanesOf, toneOf, type Exchange, type Lane, type Mark, type Range } from '../lib/steps';

// Narrow marks are common and a cursor is not, so every mark is drawn at least this wide to stay reachable.
const leastPx = 3;

const laneHeight = 18;

const gap = 4;

const top = 6;

const axis = 30;

interface Placed {
  lane: Lane;
  mark: Mark;
  x1: number;
  x2: number;
}

export function Lanes({
  marks,
  exchanges,
  range,
  selected,
  left,
  width,
  onOpen,
  onExchange,
  onHover,
}: {
  marks: readonly Mark[];
  exchanges: readonly Exchange[];
  range: Range;
  selected: string | null;
  left: number;
  width: number;
  onOpen: (step: string) => void;
  onExchange: (exchange: Exchange) => void;
  onHover: (mark: Mark | null, event: PointerEvent) => void;
}) {
  const right = Math.max(left + 10, width - 8);
  const height = top + lanes.length * (laneHeight + gap) + axis;
  const shown = useMemo(() => marks.filter((mark) => holds(range, mark.startMs, mark.endMs)), [marks, range]);

  const scale = useMemo(
    () => foldScale(shown.map((mark) => [Math.max(range[0], mark.startMs), Math.min(range[1], mark.endMs)]), left, right),
    [shown, range, left, right],
  );

  const laneY = (index: number) => top + index * (laneHeight + gap);
  const axisY = laneY(lanes.length) + 1;

  const placed: Placed[] = useMemo(
    () =>
      shown.flatMap((mark) => {
        const x1 = scale.map(Math.max(range[0], mark.startMs));
        const x2 = scale.map(Math.min(range[1], mark.endMs));

        return lanesOf(mark.step).map((lane) => ({ lane, mark, x1, x2: Math.max(x1 + leastPx, x2) }));
      }),
    [shown, scale, range],
  );

  const opened = exchanges.filter((each) => holds(range, each.startMs, each.endMs));

  return (
    <svg width={width} height={height} className="timeline-lanes" role="img" aria-label="The steps in the stretch in view">
      {lanes.map((lane, index) => (
        <g key={lane.key}>
          <text x={left - 10} y={laneY(index) + laneHeight / 2 + 4} textAnchor="end" className="timeline-label">
            {lane.label}
          </text>
          <line
            x1={left}
            x2={right}
            y1={laneY(index) + laneHeight / 2}
            y2={laneY(index) + laneHeight / 2}
            className="timeline-track"
          />
        </g>
      ))}

      {ticksOf(scale).map((tick) => (
        <g key={tick.ms}>
          <line x1={tick.x} x2={tick.x} y1={top} y2={axisY} className="timeline-grid" />
          <text x={tick.x} y={axisY + 14} textAnchor="middle" className="timeline-axis">
            {describeClock(tick.ms, true)}
          </text>
        </g>
      ))}

      {scale.folds.map((fold) => (
        <g key={fold.x}>
          <line x1={fold.x} x2={fold.x} y1={top} y2={axisY} className="timeline-fold" />
          <text x={fold.x} y={axisY + 26} textAnchor="middle" className="timeline-fold-word">
            {describeSpell(fold.toMs - fold.fromMs)} idle
          </text>
        </g>
      ))}

      {opened.map((exchange) => {
        const x1 = scale.map(Math.max(range[0], exchange.startMs));
        const x2 = scale.map(Math.min(range[1], exchange.endMs));

        return (
          <rect
            key={exchange.index}
            x={x1}
            y={laneY(0)}
            width={Math.max(leastPx, x2 - x1)}
            height={laneHeight}
            className="timeline-exchange"
            onClick={() => onExchange(exchange)}
          >
            <title>{`Exchange ${exchange.index + 1}`}</title>
          </rect>
        );
      })}

      {placed.map(({ lane, mark, x1, x2 }) => (
        <rect
          key={`${lane}-${mark.step.id}`}
          x={x1}
          y={laneY(lanes.findIndex((each) => each.key === lane)) + 3}
          width={x2 - x1}
          height={laneHeight - 6}
          rx={1}
          className={`timeline-mark is-${toneOf(mark.step)}${mark.step.id === selected ? ' is-open' : ''}`}
          onPointerEnter={(event) => onHover(mark, event)}
          onPointerLeave={(event) => onHover(null, event)}
          onClick={() => onOpen(mark.step.id)}
        />
      ))}
    </svg>
  );
}
