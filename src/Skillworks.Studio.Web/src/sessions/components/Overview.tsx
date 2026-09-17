import { useMemo, useRef, type PointerEvent } from 'react';
import { clamp, moved, rangeOf, type Range } from '../lib/view';
import { foldScale } from '../lib/fold';
import { boundsOf, describeClock, toneOf, type Mark, type Tone } from '../lib/steps';

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

function gripAt(x: number, view: Range | null): Grip {
  if (view === null) {
    return 'new';
  }

  if (Math.abs(x - view[0]) <= reachPx) {
    return 'from';
  }

  if (Math.abs(x - view[1]) <= reachPx) {
    return 'to';
  }

  return x > view[0] && x < view[1] ? 'move' : 'new';
}

export function Overview({
  marks,
  whole,
  view,
  left,
  width,
  onView,
}: {
  marks: readonly Mark[];
  whole: Range;
  view: Range | null;
  left: number;
  width: number;
  onView: (view: Range | null) => void;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const dragging = useRef<Dragging | null>(null);
  const right = Math.max(left + 10, width - 8);

  const scale = useMemo(() => foldScale(boundsOf(marks), left, right), [marks, left, right]);

  const viewPx: Range | null = view === null ? null : [scale.map(view[0]), scale.map(view[1])];
  const cursorX = (event: PointerEvent) => event.clientX - (svg.current?.getBoundingClientRect().left ?? 0);

  // A View is dragged in pixels and read in moments, so a folded idle pause is crossed at the speed it is drawn.
  const moments = (one: number, other: number): Range =>
    rangeOf(scale.invert(clamp(one, left, right)), scale.invert(clamp(other, left, right)), whole);

  const viewOf = (held: Dragging, x: number): Range => {
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
    dragging.current = { grip: gripAt(x, viewPx), fromX: x, wasX: viewPx ?? [x, x], dragged: false };
  };

  const move = (event: PointerEvent<SVGSVGElement>) => {
    const held = dragging.current;

    if (held === null) {
      return;
    }

    const x = cursorX(event);

    held.dragged ||= Math.abs(x - held.fromX) > dragPx;

    if (held.dragged) {
      onView(viewOf(held, x));
    }
  };

  const up = () => {
    const held = dragging.current;

    dragging.current = null;

    // Pressed and let go in one place: a reader who clicks the strip is asking for the whole run back.
    if (held !== null && !held.dragged) {
      onView(null);
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
        view === null
          ? 'The whole run. Drag across the strip to choose what is in view.'
          : `Reading ${describeClock(view[0], true)} to ${describeClock(view[1], true)}. Drag across the strip to change what is in view.`
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

      {viewPx !== null && (
        <>
          <rect x={left} y={2} width={Math.max(0, viewPx[0] - left)} height={height - 4} className="timeline-shade" />
          <rect x={viewPx[1]} y={2} width={Math.max(0, right - viewPx[1])} height={height - 4} className="timeline-shade" />
          <rect x={viewPx[0]} y={2} width={Math.max(2, viewPx[1] - viewPx[0])} height={height - 4} className="timeline-view" />
          <rect x={viewPx[0] - 3} y={height / 2 - 9} width={6} height={18} rx={2} className="timeline-handle" />
          <rect x={viewPx[1] - 3} y={height / 2 - 9} width={6} height={18} rx={2} className="timeline-handle" />
        </>
      )}
    </svg>
  );
}
