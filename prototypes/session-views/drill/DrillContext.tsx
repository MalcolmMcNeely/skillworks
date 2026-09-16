// PROTOTYPE — throwaway. Variant A's context chart: tokens sent on each main-thread call, with the skill in force
// behind it and the cost of each call in its own small chart beneath, on the same calls.

import { useMemo, useRef, useState, type PointerEvent } from 'react';
import type { Session } from '../sessionModel';
import { SessionTip, useTip } from '../SessionTip';
import { describe, format, type Activation, type ContextPoint } from '../sessionMeasures';
import { useWidth } from './useDrillSession';

const left = 50;
const right = 12;
const strip = 20;
const plotTop = strip + 6;
const plotHeight = 150;
const costGap = 26;
const costHeight = 46;
const costBase = plotTop + plotHeight + costGap + costHeight;
const height = costBase + 20;

function nice(value: number) {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (step * power >= value) return step * power;
  return 10 * power;
}

export function DrillContext({
  session,
  points,
  activations,
  activation,
  limit,
  onOpen,
}: {
  session: Session;
  points: ContextPoint[];
  activations: Activation[];
  activation: number | null;
  limit: number;
  onOpen: (stepId: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const width = Math.max(320, useWidth(box, 520));
  const tip = useTip();
  const [at, setAt] = useState<number | null>(null);

  const chart = useMemo(() => {
    const count = points.length;
    const step = (width - left - right) / Math.max(1, count);
    const x = (index: number) => left + (index + 0.5) * step;
    const maxTokens = nice(Math.max(...points.map((point) => point.context), 1));
    const maxCost = nice(Math.max(...points.map((point) => point.step.costUsd), 0.001));
    const y = (tokens: number) => plotTop + plotHeight - (tokens / maxTokens) * plotHeight;

    const bands: { skill: string; from: number; to: number }[] = [];
    points.forEach((point, index) => {
      const last = bands[bands.length - 1];
      if (point.step.skill === null) return;
      if (last && last.skill === point.step.skill && last.to === index - 1) last.to = index;
      else bands.push({ skill: point.step.skill, from: index, to: index });
    });

    const fired = activations
      .map((each) => ({ each, index: points.findIndex((point) => point.step.at > each.startMs) }))
      .filter(({ each, index }) => index >= 0 && points[index].step.at <= each.endMs);

    const line = points.map((point, index) => `${x(index).toFixed(1)},${y(point.context).toFixed(1)}`).join('L');

    return { count, step, x, y, maxTokens, maxCost, bands, fired, line };
  }, [points, activations, width]);

  if (points.length < 2) {
    return (
      <section className="drill-frame drill-context" aria-labelledby="drill-ctx-title">
        <div className="drill-frame-head">
          <h2 id="drill-ctx-title">Context on each call</h2>
        </div>
        <p className="drill-empty">Fewer than two main-thread model calls here.</p>
      </section>
    );
  }

  const { step, x, y, maxTokens, maxCost, bands, fired, line } = chart;
  const barWidth = Math.max(1, Math.min(10, step - 2));
  const chosen = activation === null ? null : activations[activation];
  const chosenFrom = chosen === null ? -1 : points.findIndex((point) => point.step.at > chosen.startMs);
  const chosenTo = chosen === null ? -1 : points.findLastIndex((point) => point.step.at <= chosen.endMs);

  const onMove = (event: PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - rect.left;
    const py = event.clientY - rect.top;

    if (py < plotTop) {
      const flag = fired.find(({ index }) => Math.abs(left + index * step - px) <= 8);
      if (flag) {
        setAt(null);
        tip.show(describe(flag.each.step, session), event, null);
        return;
      }
    }

    const index = Math.max(0, Math.min(points.length - 1, Math.floor((px - left) / step)));
    const point = points[index];
    const base = describe(point.step, session);
    setAt(index);
    tip.show(
      {
        ...base,
        title: `Call ${index + 1} of ${points.length} · ${format.tokens(point.context)} context`,
        rows: [
          ...base.rows,
          ...(point.rebuilt ? ([['Cache', 'rebuilt on this call']] as [string, string][]) : []),
          ...(point.compacted ? ([['Before it', 'the context was compacted']] as [string, string][]) : []),
        ],
        said: null,
      },
      event,
    );
  };

  return (
    <section className="drill-frame drill-context" aria-labelledby="drill-ctx-title">
      <div className="drill-frame-head">
        <h2 id="drill-ctx-title">Context on each call</h2>
        <span className="drill-sub">
          {points.length} main-thread calls · peak {format.tokens(Math.max(...points.map((point) => point.context)))} of {format.tokens(limit)}
        </span>
      </div>
      <div ref={box} className="drill-ctx-box">
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Context tokens and cost on each main-thread model call"
          className="drill-ctx-svg"
          onPointerMove={onMove}
          onPointerLeave={() => {
            setAt(null);
            tip.hide();
          }}
          onClick={() => {
            if (at !== null) onOpen(points[at].step.id);
          }}
        >
          {bands.map((band, index) => {
            const x1 = left + band.from * step;
            const bandWidth = (band.to - band.from + 1) * step;
            return (
              <g key={`${band.skill}-${band.from}`}>
                <rect x={x1} y={0} width={bandWidth} height={plotTop + plotHeight} className={index % 2 === 0 ? 'drill-ctx-band' : 'drill-ctx-band is-alt'} />
                <line x1={x1} x2={x1} y1={0} y2={plotTop + plotHeight} className="drill-ctx-band-edge" />
                {bandWidth > band.skill.length * 6 + 20 && (
                  <text x={x1 + 14} y={13} className="drill-t-force">
                    {band.skill}
                  </text>
                )}
              </g>
            );
          })}
          {chosenFrom >= 0 && chosenTo >= chosenFrom && (
            <rect x={left + chosenFrom * step} y={strip + 1} width={(chosenTo - chosenFrom + 1) * step} height={3} className="drill-ctx-chosen" />
          )}
          {fired.map(({ each, index }) => {
            const fx = left + index * step;
            return <path key={each.index} d={`M${fx} ${strip}V${4}L${fx + 7} ${7.5}L${fx} ${11}`} className="drill-m-skill drill-ctx-flag" />;
          })}
          {[0, maxTokens / 2, maxTokens].map((tokens) => (
            <g key={tokens}>
              <line x1={left} x2={width - right} y1={y(tokens)} y2={y(tokens)} className="drill-grid" />
              <text x={left - 6} y={y(tokens) + 3.5} textAnchor="end" className="drill-t-axis">
                {format.tokens(tokens)}
              </text>
            </g>
          ))}
          <path d={`M${x(0)},${y(0)}L${line}L${x(points.length - 1)},${y(0)}Z`} className="drill-ctx-area" />
          <path d={`M${line}`} className="drill-ctx-line" />
          {points.map((point, index) =>
            point.rebuilt ? <circle key={point.step.id} cx={x(index)} cy={y(point.context)} r={4} className="drill-ctx-ring" /> : null,
          )}
          {points.map((point, index) =>
            point.compacted ? <line key={`c${point.step.id}`} x1={x(index)} x2={x(index)} y1={plotTop} y2={plotTop + plotHeight} className="drill-ctx-compact" /> : null,
          )}

          <text x={left - 6} y={costBase - costHeight + 3.5} textAnchor="end" className="drill-t-axis">
            {format.usd(maxCost)}
          </text>
          <text x={left - 6} y={costBase + 3.5} textAnchor="end" className="drill-t-axis">
            $0
          </text>
          <line x1={left} x2={width - right} y1={costBase - costHeight} y2={costBase - costHeight} className="drill-grid" />
          <line x1={left} x2={width - right} y1={costBase} y2={costBase} className="drill-grid" />
          <text x={left} y={costBase - costHeight - 8} className="drill-t-label">
            Cost of each call
          </text>
          {points.map((point, index) => {
            const barHeight = Math.max(0.8, (point.step.costUsd / maxCost) * costHeight);
            return <rect key={point.step.id} x={x(index) - barWidth / 2} y={costBase - barHeight} width={barWidth} height={barHeight} rx={Math.min(2, barWidth / 2)} className="drill-cost-bar" />;
          })}
          <text x={left} y={costBase + 15} className="drill-t-axis">
            call 1
          </text>
          <text x={width - right} y={costBase + 15} textAnchor="end" className="drill-t-axis">
            call {points.length}
          </text>

          {at !== null && (
            <g pointerEvents="none">
              <line x1={x(at)} x2={x(at)} y1={plotTop} y2={costBase} className="drill-cross" />
              <circle cx={x(at)} cy={y(points[at].context)} r={4.5} className="drill-cross-dot" />
            </g>
          )}
        </svg>
      </div>
      <div className="drill-legend">
        <span><i className="drill-sw-main" />Context tokens</span>
        <span><i className="drill-sw-force" />Skill in force, named</span>
        <span><i className="drill-sw-flag" />Skill fired</span>
        <span><i className="drill-sw-ring" />Cache rebuilt</span>
        <span><i className="drill-sw-tool" />Cost of the call</span>
      </div>
      <SessionTip tip={tip.tip} />
    </section>
  );
}
