// PROTOTYPE — throwaway. A Cost tab: the Cost in view as it builds up over time, one step up at the end of each Turn.
import { useLayoutEffect, useMemo, useRef, useState, type PointerEvent } from 'react';
import { describeCount, describeLength, describeMoney } from '../../../../shared/figures/lib/figures';
import { foldScale, ticksOf } from '../../../lib/fold';
import { inSpell, type Spell } from '../../../lib/timeline/view';
import { describeClock, type Mark } from '../../../lib/steps';
import { isUpkeep, whyItRan } from '../../promptPrototype/StepCard';
import { useDetailsState } from '../../promptPrototype/stepDetails';

const height = 230;

// The timeline's own gutter, so the two share one x axis.
const left = 116;

const top = 14;

const axis = 34;

interface Point {
  mark: Mark;
  atMs: number;
  total: number;
}

function useWidth() {
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  useLayoutEffect(() => {
    const node = frame.current;

    if (node === null) {
      return;
    }

    const watching = new ResizeObserver(([entry]) => setWidth(Math.max(360, Math.round(entry.contentRect.width))));

    watching.observe(node);

    return () => watching.disconnect();
  }, []);

  return [frame, width] as const;
}

// About four round steps a little over the total, so the line never touches the roof and the labels read as money.
function stepsOf(total: number): number[] {
  const wanted = Math.max(total, 0.01) * 1.05;
  const rough = wanted / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((each) => each * magnitude).find((each) => each >= rough) ?? 10 * magnitude;

  return Array.from({ length: Math.ceil(wanted / step) + 1 }, (_, index) => index * step);
}

export function CostTabPrototype({
  marks,
  view,
  selected,
  onOpen,
}: {
  marks: readonly Mark[];
  view: Spell | null;
  selected: string | null;
  onOpen: (step: string) => void;
}) {
  const [frame, width] = useWidth();
  const [pointed, setPointed] = useState<Point | null>(null);
  const [asTable, setAsTable] = useState(false);
  const details = useDetailsState();

  const points = useMemo(
    () =>
      inSpell(marks, view)
        .filter((mark) => mark.step.kind === 'turn')
        .toSorted((one, other) => one.endMs - other.endMs)
        .reduce<Point[]>(
          (built, mark) => [...built, { mark, atMs: mark.endMs, total: (built.at(-1)?.total ?? 0) + mark.step.cost }],
          [],
        ),
    [marks, view],
  );

  const total = points.at(-1)?.total ?? 0;
  const yTicks = stepsOf(total);
  const roof = yTicks.at(-1) ?? 1;
  const x1 = Math.max(left + 10, width - 8);
  const baseY = height - axis;

  // Folded over every Step in view, as the lanes are, so each rise sits under the Turn that caused it.
  const scale = useMemo(
    () =>
      foldScale(
        inSpell(marks, view).map(
          (mark): Spell => (view === null ? [mark.startMs, mark.endMs] : [Math.max(view[0], mark.startMs), Math.min(view[1], mark.endMs)]),
        ),
        left,
        x1,
      ),
    [marks, view, x1],
  );

  const y = (money: number) => baseY - ((baseY - top) * money) / roof;

  // Up at the end of each Turn and flat between, as a Turn's Cost lands only once it is over.
  const startX = points.length === 0 ? left : scale.map(points[0].mark.startMs);
  const path = [`M ${startX} ${y(0)}`, ...points.flatMap((point) => [`H ${scale.map(point.atMs)}`, `V ${y(point.total)}`]), `H ${x1}`].join(' ');
  const wash = `${path} V ${baseY} H ${startX} Z`;

  const hover = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - box.left;
    let nearest: Point | null = null;

    for (const point of points) {
      if (nearest === null || Math.abs(scale.map(point.atMs) - px) < Math.abs(scale.map(nearest.atMs) - px)) {
        nearest = point;
      }
    }

    setPointed(nearest);
  };

  const pointedDetail = pointed === null ? undefined : details.byStep.get(pointed.mark.step.id);
  const pointedWhy = pointedDetail?.kind === 'turn' ? whyItRan(pointedDetail.source) : null;
  const pointedUpkeep = pointedDetail?.kind === 'turn' && isUpkeep(pointedDetail);
  const tipX = pointed === null ? 0 : scale.map(pointed.atMs);

  return (
    <>
      <header className="panel-head pp-cost-head">
        <p className="micro panel-figure">
          {describeCount(points.length)} turns · {describeMoney(total)}
          {view === null ? '' : ' in view'}
        </p>
        <button type="button" className="timeline-clear" onClick={() => setAsTable(!asTable)} aria-pressed={asTable}>
          {asTable ? 'Show the chart' : 'Show as a table'}
        </button>
      </header>

      <div className="pp-cost-frame" ref={frame}>
      {points.length === 0 ? (
        <p className="session-word">{view === null ? 'This run made no turn.' : 'No turn in view.'}</p>
      ) : asTable ? (
        <table className="pp-cost-table">
          <thead>
            <tr>
              <th scope="col">Ended</th>
              <th scope="col">Why it ran</th>
              <th scope="col">Took</th>
              <th scope="col">Cost</th>
              <th scope="col">So far</th>
            </tr>
          </thead>
          <tbody>
            {points.map((point) => {
              const detail = details.byStep.get(point.mark.step.id);

              return (
                <tr key={point.mark.step.id} className={point.mark.step.id === selected ? 'is-open' : ''}>
                  <td>{describeClock(point.atMs, true)}</td>
                  <td>
                    <button type="button" className="pp-cost-open" onClick={() => onOpen(point.mark.step.id)}>
                      {detail?.kind === 'turn' ? whyItRan(detail.source) : 'Turn'}
                    </button>
                  </td>
                  <td>{describeLength(point.mark.step.lengthMs)}</td>
                  <td>{describeMoney(point.mark.step.cost)}</td>
                  <td>{describeMoney(point.total)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <>
          <svg
            width={width}
            height={height}
            className="pp-cost-plot"
            role="img"
            aria-label={`The Cost ${view === null ? 'of the whole run' : 'in view'} as it built up, to ${describeMoney(total)}`}
            onPointerMove={hover}
            onPointerLeave={() => setPointed(null)}
            onClick={() => pointed && onOpen(pointed.mark.step.id)}
          >
            {yTicks.map((tick) => (
              <g key={tick}>
                <line x1={left} x2={x1} y1={y(tick)} y2={y(tick)} className="pp-cost-grid" />
                <text x={left - 8} y={y(tick) + 4} textAnchor="end" className="timeline-axis">
                  {describeMoney(tick)}
                </text>
              </g>
            ))}

            {ticksOf(scale).map((tick) => (
              <text key={tick.ms} x={tick.x} y={baseY + 16} textAnchor="middle" className="timeline-axis">
                {describeClock(tick.ms, true)}
              </text>
            ))}

            {/* The lanes above already say how long each fold sat idle, so the line alone marks it here. */}
            {scale.folds.map((fold) => (
              <line key={fold.x} x1={fold.x} x2={fold.x} y1={top} y2={baseY} className="timeline-fold" />
            ))}

            <path d={wash} className="pp-cost-wash" />
            <path d={path} className="pp-cost-line" />
            <circle cx={x1} cy={y(total)} r={4} className="pp-cost-dot" />
            <text x={x1} y={y(total) - 10} textAnchor="end" className="pp-cost-end">
              {describeMoney(total)}
            </text>

            {points
              .filter((point) => point.mark.step.id === selected)
              .map((point) => (
                <line
                  key={point.mark.step.id}
                  x1={scale.map(point.atMs)}
                  x2={scale.map(point.atMs)}
                  y1={top}
                  y2={baseY}
                  className="pp-cost-opened"
                />
              ))}

            {pointed === null ? null : (
              <>
                <line x1={tipX} x2={tipX} y1={top} y2={baseY} className="pp-cost-cross" />
                <circle cx={tipX} cy={y(pointed.total)} r={4} className="pp-cost-dot" />
              </>
            )}
          </svg>

          {pointed === null ? null : (
            <div
              className="timeline-tip pp-cost-tip"
              style={{ left: Math.min(tipX + 12, width - 250), top: Math.max(0, y(pointed.total) - 70) }}
              role="status"
            >
              <p className="pp-cost-tip-value">{describeMoney(pointed.total)} so far</p>
              <p className="micro">
                +{describeMoney(pointed.mark.step.cost)} this Turn · ended {describeClock(pointed.atMs, true)}
              </p>
              {pointedWhy === null ? null : <p className={`pp-brief-line${pointedUpkeep ? ' pp-upkeep' : ''}`}>{pointedWhy}</p>}
              <p className="micro pp-dim">Click to open it</p>
            </div>
          )}
        </>
      )}
      </div>
    </>
  );
}
