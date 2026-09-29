import { useMemo } from 'react';
import { describeCount, describeMoney } from '../../../../shared/figures/lib/figures';
import { foldScale, ticksOf } from '../../../lib/fold';
import { moneyTicksOf, turnsOf } from '../../../lib/timeline/cost';
import { clamp, inSpell, type Spell } from '../../../lib/timeline/view';
import { describeClock, type Mark } from '../../../lib/steps';
import { gutter as left, useWidth } from '../frame';

const height = 230;

const top = 14;

const axis = 34;

function clip(view: Spell | null, ms: number): number {
  return view === null ? ms : clamp(ms, view[0], view[1]);
}

// Every figure here reads the View alone, and a Highlight is no input, so lighting a skill never moves the line.
export function CostTab({ marks, view }: { marks: readonly Mark[]; view: Spell | null }) {
  const [frame, width] = useWidth<HTMLDivElement>();
  const turns = useMemo(() => turnsOf(marks, view), [marks, view]);
  const madeNone = useMemo(() => turnsOf(marks, null).length === 0, [marks]);

  const total = turns.at(-1)?.soFar ?? 0;
  const moneyTicks = moneyTicksOf(total);
  const roof = moneyTicks.at(-1) ?? 1;
  const right = Math.max(left + 10, width - 8);
  const baseY = height - axis;

  // Built over every Step in view and clipped as the lanes are, so each rise sits under the Turn that caused it.
  const scale = useMemo(
    () => foldScale(inSpell(marks, view).map((mark): Spell => [clip(view, mark.startMs), clip(view, mark.endMs)]), left, right),
    [marks, view, right],
  );

  const y = (money: number) => baseY - ((baseY - top) * money) / roof;
  const startX = scale.map(clip(view, Math.min(...turns.map((turn) => turn.mark.startMs))));
  const line = [
    `M ${startX} ${y(0)}`,
    ...turns.flatMap((turn) => [`H ${scale.map(clip(view, turn.mark.endMs))}`, `V ${y(turn.soFar)}`]),
    `H ${right}`,
  ].join(' ');
  const wash = `${line} V ${baseY} H ${startX} Z`;

  return (
    <>
      <header className="panel-head">
        <p className="micro panel-figure">
          {describeCount(turns.length)} turns · {describeMoney(total)}
          {view === null ? '' : ' in view'}
        </p>
      </header>

      <div className="cost-frame" ref={frame}>
        {turns.length === 0 ? (
          <p className="session-word">{madeNone ? 'This run made no turn.' : 'No turn in view.'}</p>
        ) : (
          <svg
            width={width}
            height={height}
            className="cost-plot"
            role="img"
            aria-label={`The Cost ${view === null ? 'of the whole run' : 'in view'} as it built up, to ${describeMoney(total)}`}
          >
            {moneyTicks.map((money) => (
              <g key={money}>
                <line x1={left} x2={right} y1={y(money)} y2={y(money)} className="cost-grid" />
                <text x={left - 8} y={y(money) + 4} textAnchor="end" className="timeline-axis">
                  {describeMoney(money)}
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

            <path d={wash} className="cost-wash" />
            <path d={line} className="cost-line" />
            <circle cx={right} cy={y(total)} r={4} className="cost-dot" />
            <text x={right} y={y(total) - 10} textAnchor="end" className="cost-end">
              {describeMoney(total)}
            </text>
          </svg>
        )}
      </div>
    </>
  );
}
