import type { Moment } from '../../lib/verdict/moment';
import { lanes, lanesOf, toneOf } from '../../lib/steps';

const width = 300;

const laneHeight = 6;

const gap = 2;

// A mark narrower than this vanishes once the drawing is scaled down to a card.
const leastWidth = 1.5;

export function MomentDrawing({ moment, from, to }: { moment: Moment; from: number; to: number }) {
  const [start, end] = moment.spell;
  const x = (ms: number) => ((Math.min(end, Math.max(start, ms)) - start) / Math.max(1, end - start)) * width;
  const laneY = (lane: string) => lanes.findIndex((each) => each.key === lane) * (laneHeight + gap);
  const height = lanes.length * (laneHeight + gap);

  return (
    <svg
      className="moment-drawing"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="The steps around the moment this happened"
    >
      <rect x={x(from)} y={0} width={Math.max(leastWidth, x(to) - x(from))} height={height} className="moment-spell" />
      {moment.marks.flatMap((mark) =>
        lanesOf(mark.step).map((lane) => (
          <rect
            key={`${lane}-${mark.step.id}`}
            x={x(mark.startMs)}
            y={laneY(lane)}
            width={Math.max(leastWidth, x(mark.endMs) - x(mark.startMs))}
            height={laneHeight}
            className={`timeline-strip is-${toneOf(mark.step)}`}
          />
        )),
      )}
    </svg>
  );
}
