import { useMemo, useState, type PointerEvent } from 'react';
import { describeCount, describeMoney } from '../../../../shared/figures/lib/figures';
import { foldScale, ticksOf } from '../../../lib/fold';
import type { StepDetails } from '../../../lib/details';
import { moneyTicksOf, nearestTurnOf, purposeWordsOf, skillWordsOf, turnsOf, type CostTurn } from '../../../lib/timeline/cost';
import { clamp, inSpell, type Spell } from '../../../lib/timeline/view';
import { describeClock, type Mark } from '../../../lib/steps';
import { gutter as left, useWidth } from '../frame';
import { CostTable } from './CostTable';

const height = 230;

const top = 14;

const axis = 34;

interface Pointed {
  turn: CostTurn;
  x: number;
  y: number;
}

function clip(view: Spell | null, ms: number): number {
  return view === null ? ms : clamp(ms, view[0], view[1]);
}

// The Cost so far leads, as that is the figure the reader pointed at the line to learn.
function Tip({ pointed, details }: { pointed: Pointed; details: StepDetails | null }) {
  const { turn } = pointed;
  const purpose = purposeWordsOf(turn.mark.step, details);

  return (
    <div className="timeline-tip" style={{ left: pointed.x, top: pointed.y }} role="status">
      <p className="timeline-tip-head">{describeMoney(turn.soFar)} so far</p>
      <p className="micro">
        This turn {describeMoney(turn.mark.step.cost)} · ended {describeClock(turn.mark.endMs, true)}
      </p>
      <p className="timeline-tip-words">{skillWordsOf(turn.mark.step)}</p>
      {purpose === null ? null : <p className="timeline-tip-words">{purpose}</p>}
    </div>
  );
}

// Every figure here reads the View alone, and a Highlight is no input, so lighting a skill never moves the line.
export function CostTab({
  marks,
  view,
  selected,
  details,
  onOpen,
}: {
  marks: readonly Mark[];
  view: Spell | null;
  selected: string | null;
  details: StepDetails | null;
  onOpen: (step: string) => void;
}) {
  const [frame, width] = useWidth<HTMLDivElement>();
  const [pointed, setPointed] = useState<Pointed | null>(null);
  // Held here and never in the address, the same as which tab is shown.
  const [asTable, setAsTable] = useState(false);
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

  const xOf = (ms: number) => scale.map(clip(view, ms));
  const y = (money: number) => baseY - ((baseY - top) * money) / roof;
  const startX = xOf(Math.min(...turns.map((turn) => turn.mark.startMs)));
  const line = [
    `M ${startX} ${y(0)}`,
    ...turns.flatMap((turn) => [`H ${xOf(turn.mark.endMs)}`, `V ${y(turn.soFar)}`]),
    `H ${right}`,
  ].join(' ');
  const wash = `${line} V ${baseY} H ${startX} Z`;
  const open = inSpell(marks, view).find((mark) => mark.step.id === selected) ?? null;

  const point = (event: PointerEvent<SVGSVGElement>) => {
    const box = frame.current?.getBoundingClientRect();
    const x = event.clientX - (box?.left ?? 0);
    const turn = nearestTurnOf(turns, scale.invert(x));

    setPointed(turn === null ? null : { turn, x: x + 14, y: event.clientY - (box?.top ?? 0) + 14 });
  };

  return (
    <>
      <header className="panel-head">
        <p className="micro panel-figure">
          {describeCount(turns.length)} turns · {describeMoney(total)}
          {view === null ? '' : ' in view'}
        </p>
        <button type="button" className="panel-switch" aria-pressed={asTable} onClick={() => setAsTable(!asTable)}>
          Show as a table
        </button>
      </header>

      <div className="cost-frame" ref={frame}>
        {turns.length === 0 ? (
          <p className="session-word">{madeNone ? 'This run made no turn.' : 'No turn in view.'}</p>
        ) : asTable ? (
          <CostTable turns={turns} selected={selected} onOpen={onOpen} />
        ) : (
          <svg
            width={width}
            height={height}
            className="cost-plot"
            role="img"
            aria-label={`The Cost ${view === null ? 'of the whole run' : 'in view'} as it built up, to ${describeMoney(total)}`}
            onPointerMove={point}
            onPointerLeave={() => setPointed(null)}
            onClick={() => (pointed === null ? undefined : onOpen(pointed.turn.mark.step.id))}
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

            {open === null ? null : (
              <line x1={xOf(open.startMs)} x2={xOf(open.startMs)} y1={top} y2={baseY} className="cost-open" />
            )}

            {pointed === null ? null : (
              <g className="cost-cross">
                <line x1={xOf(pointed.turn.mark.endMs)} x2={xOf(pointed.turn.mark.endMs)} y1={top} y2={baseY} />
                <circle cx={xOf(pointed.turn.mark.endMs)} cy={y(pointed.turn.soFar)} r={3.5} />
              </g>
            )}
          </svg>
        )}
        {pointed === null || asTable ? null : <Tip pointed={pointed} details={details} />}
      </div>
    </>
  );
}
