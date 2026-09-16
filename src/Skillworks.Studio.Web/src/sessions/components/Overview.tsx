import { useMemo, useRef, type PointerEvent } from 'react';
import { clamp, moved, rangeOf } from '../lib/brush';
import { foldScale } from '../lib/fold';
import { describeClock, stretchesOf, toneOf, type Mark, type Range, type Tone } from '../lib/steps';

const reachPx = 7;

// A cursor never comes to rest where it was pressed, so a click needs this much give before it is a drag.
const dragPx = 3;

const height = 44;

type Grip = 'new' | 'move' | 'from' | 'to';

interface Dragging {
  grip: Grip;
  fromX: number;
  wasX: Range;
  dragged: boolean;
}

// Three rows and no more, so a run's shape reads at a glance on a strip a few pixels tall.
const rows: Record<Tone, number> = { model: 0, tool: 1, refused: 1, fault: 2 };

function gripAt(x: number, brush: Range | null): Grip {
  if (brush === null) {
    return 'new';
  }

  if (Math.abs(x - brush[0]) <= reachPx) {
    return 'from';
  }

  if (Math.abs(x - brush[1]) <= reachPx) {
    return 'to';
  }

  return x > brush[0] && x < brush[1] ? 'move' : 'new';
}

export function Overview({
  marks,
  whole,
  range,
  left,
  width,
  onRange,
}: {
  marks: readonly Mark[];
  whole: Range;
  range: Range | null;
  left: number;
  width: number;
  onRange: (range: Range | null) => void;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const dragging = useRef<Dragging | null>(null);
  const right = Math.max(left + 10, width - 8);

  const scale = useMemo(() => foldScale(stretchesOf(marks), left, right), [marks, left, right]);

  const brush: Range | null = range === null ? null : [scale.map(range[0]), scale.map(range[1])];
  const cursorX = (event: PointerEvent) => event.clientX - (svg.current?.getBoundingClientRect().left ?? 0);

  // The brush is dragged in pixels and read in moments, so a folded idle stretch is crossed at the speed it is drawn.
  const moments = (one: number, other: number): Range =>
    rangeOf(scale.invert(clamp(one, left, right)), scale.invert(clamp(other, left, right)), whole);

  const stretched = (held: Dragging, x: number): Range => {
    const by = x - held.fromX;

    if (held.grip === 'new') {
      return moments(held.fromX, x);
    }

    if (held.grip === 'from') {
      return moments(held.wasX[0] + by, held.wasX[1]);
    }

    if (held.grip === 'to') {
      return moments(held.wasX[0], held.wasX[1] + by);
    }

    const [fromX, toX] = moved(held.wasX, by, [left, right]);

    return moments(fromX, toX);
  };

  const down = (event: PointerEvent<SVGSVGElement>) => {
    const x = cursorX(event);

    if (x < left - reachPx) {
      return;
    }

    event.currentTarget.setPointerCapture(event.pointerId);
    dragging.current = { grip: gripAt(x, brush), fromX: x, wasX: brush ?? [x, x], dragged: false };
  };

  const move = (event: PointerEvent<SVGSVGElement>) => {
    const held = dragging.current;

    if (held === null) {
      return;
    }

    const x = cursorX(event);

    held.dragged ||= Math.abs(x - held.fromX) > dragPx;

    if (held.dragged) {
      onRange(stretched(held, x));
    }
  };

  const up = () => {
    const held = dragging.current;

    dragging.current = null;

    // Pressed and let go in one place: a reader who clicks the strip is asking for the whole run back.
    if (held !== null && !held.dragged) {
      onRange(null);
    }
  };

  return (
    <svg
      ref={svg}
      className="timeline-overview"
      width={width}
      height={height}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
      role="img"
      aria-label={
        range === null
          ? 'The whole run. Drag across the strip to read one stretch of it.'
          : `Reading ${describeClock(range[0], true)} to ${describeClock(range[1], true)}. Drag across the strip to read another stretch.`
      }
    >
      <text x={left - 10} y={height / 2 + 4} textAnchor="end" className="timeline-label">
        Whole run
      </text>
      <rect x={left} y={4} width={right - left} height={height - 8} className="timeline-ground" />

      {scale.folds.map((fold) => (
        <line key={fold.x} x1={fold.x} x2={fold.x} y1={4} y2={height - 4} className="timeline-fold" />
      ))}

      {marks.map((mark) => (
        <rect
          key={mark.step.id}
          x={scale.map(mark.startMs)}
          y={8 + rows[toneOf(mark.step)] * 10}
          width={Math.max(1, scale.map(mark.endMs) - scale.map(mark.startMs))}
          height={6}
          className={`timeline-strip is-${toneOf(mark.step)}`}
        />
      ))}

      {brush !== null && (
        <>
          <rect x={left} y={2} width={Math.max(0, brush[0] - left)} height={height - 4} className="timeline-shade" />
          <rect x={brush[1]} y={2} width={Math.max(0, right - brush[1])} height={height - 4} className="timeline-shade" />
          <rect x={brush[0]} y={2} width={Math.max(2, brush[1] - brush[0])} height={height - 4} className="timeline-brush" />
          <rect x={brush[0] - 3} y={height / 2 - 9} width={6} height={18} rx={2} className="timeline-handle" />
          <rect x={brush[1] - 3} y={height / 2 - 9} width={6} height={18} rx={2} className="timeline-handle" />
        </>
      )}
    </svg>
  );
}
