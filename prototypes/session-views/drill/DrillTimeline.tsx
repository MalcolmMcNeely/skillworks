// PROTOTYPE — throwaway. Variant A's lane timeline: one row per kind of step, with idle stretches folded.

import { memo, useMemo, useRef, useState, type PointerEvent } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import { SessionTip, useTip } from '../SessionTip';
import {
  describe,
  foldScale,
  format,
  lanes,
  lanesOf,
  startOf,
  ticks,
  type Activation,
  type Description,
  type FoldScale,
  type Lane,
} from '../sessionMeasures';
import { useWidth } from './useDrillSession';

type Tone = 'main' | 'other' | 'sub' | 'tool' | 'fail' | 'warn' | 'hook' | 'skill' | 'prompt';

interface Mark {
  lane: Lane;
  x1: number;
  x2: number;
  step: SessionStep;
  shape: 'bar' | 'diamond' | 'flag' | 'tri';
  tone: Tone;
  waitX: number | null;
  track: number;
  tracks: number;
}

const laneBand = (mark: Mark, row: { y: number; h: number }) => {
  const pad = mark.tracks > 1 ? 0.5 : mark.lane === 'subagent' ? 1 : 2;
  const inner = row.h + (mark.tracks > 1 ? 4 : 0) - pad * 2;
  const first = row.y - (mark.tracks > 1 ? 2 : 0) + pad;
  const each = inner / mark.tracks;
  return { y: first + mark.track * each, h: Math.max(1.5, each - (mark.tracks > 1 ? 1 : 0)) };
};

interface Row {
  key: Lane;
  label: string;
  y: number;
  h: number;
}

interface Band {
  index: number;
  x1: number;
  x2: number;
  label: string;
}

type Hit = { mark: Mark } | { prompt: number } | { activation: number } | { gap: number } | null;

const heights: Record<Lane, number> = { prompt: 22, skill: 20, main: 14, other: 14, subagent: 14, shell: 12, edit: 12, read: 12, tool: 12, hook: 12, fault: 14 };
const left = 118;
const right = 14;
const top = 6;
const laneGap = 5;

const rows: Row[] = (() => {
  let y = top;
  return lanes.map((lane) => {
    const row = { ...lane, y, h: heights[lane.key] };
    y += row.h + laneGap;
    return row;
  });
})();
const rowOf = new Map(rows.map((row) => [row.key, row]));
const plotBottom = rows[rows.length - 1].y + rows[rows.length - 1].h + 3;
const height = plotBottom + 24;

const toneOf = (step: SessionStep, lane: Lane): Tone => {
  if (lane === 'fault') return step.kind === 'rejected' || (step.kind === 'tool' && step.errorType === 'HookBlocked') || step.kind === 'hook' ? 'warn' : 'fail';
  switch (step.kind) {
    case 'model':
      return step.thread === 'main' ? 'main' : 'other';
    case 'subagent':
      return 'sub';
    case 'tool':
      return step.ok ? 'tool' : 'fail';
    case 'hook':
      return step.blocking > 0 ? 'warn' : 'hook';
    case 'skill':
      return 'skill';
    default:
      return 'prompt';
  }
};

const Marks = memo(function Marks({
  marks,
  prompts,
  bands,
  scale,
  width,
  zoomed,
  activation,
  lit,
  selected,
}: {
  marks: Mark[];
  prompts: Band[];
  bands: Band[];
  scale: FoldScale;
  width: number;
  zoomed: boolean;
  activation: number | null;
  lit: Set<string> | null;
  selected: string | null;
}) {
  const axis = ticks(scale, 70);
  const prompt = rowOf.get('prompt')!;
  const skill = rowOf.get('skill')!;

  return (
    <g>
      {rows.map((row) => (
        <g key={row.key}>
          <text x={left - 10} y={row.y + row.h / 2 + 3.5} textAnchor="end" className="drill-t-label">
            {row.label}
          </text>
          <rect x={left} y={row.y + row.h / 2 - 0.5} width={Math.max(0, width - right - left)} height={1} className="drill-track" />
        </g>
      ))}
      {axis.map((tick) => (
        <g key={tick.ms}>
          <line x1={tick.x} x2={tick.x} y1={top - 2} y2={plotBottom} className="drill-grid" />
          <text x={tick.x} y={plotBottom + 14} textAnchor="middle" className="drill-t-axis">
            {tick.label}
          </text>
        </g>
      ))}
      {scale.gaps.map((gap) => (
        <g key={gap.fromMs} className="drill-fold">
          <line x1={gap.x - 2} x2={gap.x - 2} y1={top} y2={plotBottom} />
          <line x1={gap.x + 2} x2={gap.x + 2} y1={top} y2={plotBottom} />
        </g>
      ))}
      {prompts.map((band) => (
        <g key={band.index}>
          <rect x={band.x1} y={prompt.y} width={Math.max(3, band.x2 - band.x1)} height={prompt.h} className="drill-band" />
          {band.x2 - band.x1 > 30 && !zoomed && (
            <text x={band.x1 + 5} y={prompt.y + 15} className="drill-t-band">
              {band.label}
            </text>
          )}
        </g>
      ))}
      {bands.map((band) => {
        const wide = band.x2 - band.x1;
        return (
          <g key={band.index} className={`drill-force${band.index === activation ? ' is-on' : ''}`}>
            <rect x={band.x1} y={skill.y + 3} width={Math.max(2, wide)} height={skill.h - 6} />
            {wide > band.label.length * 6.2 + 18 && (
              <text x={band.x1 + 12} y={skill.y + skill.h / 2 + 3.5} className="drill-t-force">
                {band.label}
              </text>
            )}
          </g>
        );
      })}
      <g className={lit === null ? '' : 'drill-has-lit'}>
        {marks.map((mark) => {
          const row = rowOf.get(mark.lane)!;
          const on = lit?.has(mark.step.id) ? ' is-lit' : '';
          const cls = `drill-mk drill-m-${mark.tone}${on}`;
          if (mark.shape === 'diamond') {
            const cy = row.y + row.h / 2;
            return <path key={`${mark.step.id}-${mark.lane}`} d={`M${mark.x1} ${cy - 5}L${mark.x1 + 5} ${cy}L${mark.x1} ${cy + 5}L${mark.x1 - 5} ${cy}Z`} className={cls} />;
          }
          if (mark.shape === 'flag') {
            return <path key={`${mark.step.id}-${mark.lane}`} d={`M${mark.x1} ${row.y + row.h}V${row.y}L${mark.x1 + 8} ${row.y + 4}L${mark.x1} ${row.y + 8}`} className={cls} />;
          }
          if (mark.shape === 'tri') {
            return <path key={`${mark.step.id}-${mark.lane}`} d={`M${mark.x1 - 4.5} ${row.y - 1}H${mark.x1 + 4.5}L${mark.x1} ${row.y + 7}Z`} className={cls} />;
          }
          const band = laneBand(mark, row);
          return (
            <g key={`${mark.step.id}-${mark.lane}`}>
              <rect x={mark.x1} y={band.y} width={Math.max(1.5, mark.x2 - mark.x1)} height={band.h} rx={1} className={cls} />
              {mark.waitX !== null && mark.waitX - mark.x1 > 1 && <rect x={mark.x1} y={row.y - 1} width={mark.waitX - mark.x1} height={2} className="drill-m-wait" />}
            </g>
          );
        })}
      </g>
      {selected !== null &&
        marks
          .filter((mark) => mark.step.id === selected)
          .map((mark) => {
            const row = rowOf.get(mark.lane)!;
            return <rect key={`${mark.step.id}-${mark.lane}`} x={mark.x1 - 4} y={row.y - 3} width={Math.max(8, mark.x2 - mark.x1 + 8)} height={row.h + 6} className="drill-selected" />;
          })}
    </g>
  );
});

export function DrillTimeline({
  session,
  zoomed,
  activations,
  activation,
  lit,
  selected,
  onOpen,
  onZoom,
  onActivation,
}: {
  session: Session;
  zoomed: number | null;
  activations: Activation[];
  activation: number | null;
  lit: Set<string> | null;
  selected: string | null;
  onOpen: (stepId: string) => void;
  onZoom: (prompt: number | null) => void;
  onActivation: (index: number) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const width = Math.max(640, useWidth(box));
  const tip = useTip();
  const [hit, setHit] = useState<Hit>(null);

  const steps = useMemo(() => (zoomed === null ? session.steps : session.steps.filter((step) => step.prompt === zoomed)), [session, zoomed]);

  const promptInfo = useMemo(
    () =>
      session.prompts.map((span) => {
        const inPrompt = session.steps.filter((step) => step.prompt === span.index);
        return {
          calls: inPrompt.filter((step) => step.kind === 'model').length,
          tools: inPrompt.filter((step) => step.kind === 'tool').length,
          failed: inPrompt.filter((step) => (step.kind === 'tool' && !step.ok) || step.kind === 'modelError').length,
          cost: inPrompt.reduce((sum, step) => sum + (step.kind === 'model' ? step.costUsd : 0), 0),
        };
      }),
    [session],
  );

  const scale = useMemo(() => foldScale(steps.map((step) => [startOf(step), step.at]), left, width - right), [steps, width]);

  const { marks, byLane, prompts, bands } = useMemo(() => {
    const out: Mark[] = [];
    for (const step of steps) {
      for (const lane of lanesOf(step)) {
        const tone = toneOf(step, lane);
        const at = scale.map(step.at);
        if (lane === 'prompt') out.push({ lane, x1: at, x2: at, step, shape: 'tri', tone, waitX: null, track: 0, tracks: 1 });
        else if (lane === 'skill') out.push({ lane, x1: at, x2: at, step, shape: 'flag', tone, waitX: null, track: 0, tracks: 1 });
        else if (lane === 'fault') out.push({ lane, x1: at, x2: at, step, shape: 'diamond', tone, waitX: null, track: 0, tracks: 1 });
        else {
          const waitX = step.kind === 'tool' && step.waitedMs > 0 ? scale.map(startOf(step) + step.waitedMs) : null;
          out.push({ lane, x1: scale.map(startOf(step)), x2: at, step, shape: 'bar', tone, waitX, track: 0, tracks: 1 });
        }
      }
    }
    // Subagents run side by side, so their lanes split into tracks; one track would draw them as a single bar.
    for (const lane of ['subagent', 'other'] as Lane[]) {
      const ends: number[] = [];
      const packed = out.filter((mark) => mark.lane === lane && mark.shape === 'bar').toSorted((a, b) => a.x1 - b.x1);
      for (const mark of packed) {
        let track = ends.findIndex((end) => end <= mark.x1);
        if (track < 0) track = ends.length < 3 ? ends.length : ends.indexOf(Math.min(...ends));
        ends[track] = mark.x2 + 1;
        mark.track = track;
      }
      for (const mark of packed) mark.tracks = Math.max(1, ends.length);
    }
    // Wide bars first, so a short step drawn over a long one stays visible.
    const drawn = out.toSorted((a, b) => b.x2 - b.x1 - (a.x2 - a.x1));
    const grouped = new Map<Lane, Mark[]>();
    for (const mark of drawn) grouped.set(mark.lane, [...(grouped.get(mark.lane) ?? []), mark]);

    const inScope = session.prompts.filter((span) => zoomed === null || span.index === zoomed);
    return {
      marks: drawn,
      byLane: grouped,
      prompts: inScope.map((span) => ({ index: span.index, x1: scale.map(span.startMs), x2: scale.map(span.endMs), label: `P${span.index + 1}` })),
      bands: activations
        .filter((each) => zoomed === null || each.prompt.index === zoomed)
        .map((each) => ({ index: each.index, x1: scale.map(each.startMs), x2: scale.map(each.endMs), label: each.step.skill })),
    };
  }, [steps, scale, session, zoomed, activations]);

  const find = (x: number, y: number): Hit => {
    if (y > plotBottom || x < left - 4) return null;
    for (let index = 0; index < scale.gaps.length; index += 1) {
      if (Math.abs(x - scale.gaps[index].x) <= 5) return { gap: index };
    }
    const row = rows.find((each) => y >= each.y - laneGap / 2 - 0.5 && y <= each.y + each.h + laneGap / 2 + 0.5);
    if (row === undefined) return null;

    let best: Mark | null = null;
    let bestDistance = 8;
    for (const mark of byLane.get(row.key) ?? []) {
      if (mark.tracks > 1) {
        const band = laneBand(mark, row);
        if (y < band.y - 1.5 || y > band.y + band.h + 1.5) continue;
      }
      const distance = x < mark.x1 ? mark.x1 - x : x > mark.x2 ? x - mark.x2 : 0;
      if (distance < bestDistance || (distance === 0 && bestDistance === 0 && best !== null && mark.x2 - mark.x1 < best.x2 - best.x1)) {
        best = mark;
        bestDistance = distance;
      }
    }
    if (best !== null) return { mark: best };
    if (row.key === 'prompt') {
      const band = prompts.find((each) => x >= each.x1 - 2 && x <= each.x2 + 2);
      if (band) return { prompt: band.index };
    }
    if (row.key === 'skill') {
      const band = bands.findLast((each) => x >= each.x1 && x <= each.x2);
      if (band) return { activation: band.index };
    }
    return null;
  };

  const explain = (found: Hit): { description: Description; hint: string | null } | null => {
    if (found === null) return null;
    if ('mark' in found) return { description: describe(found.mark.step, session), hint: 'Click for the trace' };
    if ('gap' in found) {
      const gap = scale.gaps[found.gap];
      return {
        description: { title: `Folded: ${format.duration(gap.toMs - gap.fromMs)} with nothing running`, when: `${format.clock(gap.fromMs, true)} to ${format.clock(gap.toMs, true)}`, rows: [], said: null, code: null, tone: null },
        hint: null,
      };
    }
    if ('prompt' in found) {
      const span = session.prompts[found.prompt];
      const info = promptInfo[found.prompt];
      const typed = session.steps.find((step) => step.id === span.stepId);
      return {
        description: {
          title: `Prompt ${found.prompt + 1}`,
          when: `${format.clock(span.startMs, true)} · ${format.duration(span.endMs - span.startMs)}`,
          rows: [
            ['Model calls', String(info.calls)],
            ['Tool calls', String(info.tools)],
            ['Failed', String(info.failed)],
            ['Cost', format.usd(info.cost)],
          ],
          said: typed?.kind === 'prompt' ? { label: 'Typed', said: typed.said } : null,
          code: null,
          tone: null,
        },
        hint: zoomed === null ? 'Click to zoom in on this prompt' : null,
      };
    }
    const each = activations[found.activation];
    return {
      description: {
        title: `${each.step.skill} in force`,
        when: `${format.clock(each.startMs, true)} · ${format.duration(each.endMs - each.startMs)}`,
        rows: [
          ['Why', format.trigger(each.step.trigger)],
          ['Called from', each.calledFrom ?? 'nothing'],
          ['Model calls', String(each.modelCalls)],
          ['Tool calls', String(each.toolCalls)],
          ['Cost', format.usd(each.costUsd)],
        ],
        said: null,
        code: null,
        tone: null,
      },
      hint: 'Click to open it in Skill calls',
    };
  };

  const onMove = (event: PointerEvent<SVGSVGElement>) => {
    const frame = event.currentTarget.getBoundingClientRect();
    const found = find(event.clientX - frame.left, event.clientY - frame.top);
    setHit(found);
    const said = explain(found);
    if (said === null) tip.hide();
    else tip.show(said.description, event, said.hint);
  };

  const onClick = () => {
    if (hit === null) return;
    if ('mark' in hit) onOpen(hit.mark.step.id);
    else if ('prompt' in hit && zoomed === null) onZoom(hit.prompt);
    else if ('activation' in hit) onActivation(hit.activation);
    tip.hide();
  };

  const hovered = hit !== null && 'mark' in hit ? hit.mark : null;
  const hoveredRow = hovered === null ? null : rowOf.get(hovered.lane)!;
  const pick = session.prompts.length > 1;

  return (
    <section className="drill-frame drill-timeline" aria-labelledby="drill-tl-title">
      <div className="drill-frame-head">
        <h2 id="drill-tl-title">What happened, when</h2>
        <span className="drill-sub">
          {zoomed === null ? `${session.prompts.length} prompts · idle stretches over 3 minutes fold to a double line` : `Prompt ${zoomed + 1} of ${session.prompts.length}`}
        </span>
        <div className="drill-zoom">
          <button type="button" className="drill-key" disabled={zoomed === null} onClick={() => onZoom(null)}>
            ⤢ Whole session
          </button>
          {pick && (
            <>
              <button type="button" className="drill-key" aria-label="Previous prompt" disabled={zoomed === 0} onClick={() => onZoom(zoomed === null ? session.prompts.length - 1 : zoomed - 1)}>
                ◂
              </button>
              <label className="drill-picker">
                <span className="drill-hidden">Prompt</span>
                <select value={zoomed ?? -1} onChange={(event) => onZoom(Number(event.target.value) < 0 ? null : Number(event.target.value))}>
                  <option value={-1}>All prompts</option>
                  {session.prompts.map((span) => (
                    <option key={span.index} value={span.index}>
                      P{span.index + 1} · {format.clock(span.startMs)} · {format.short(span.endMs - span.startMs)} · {format.usd(promptInfo[span.index].cost)}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="drill-key" aria-label="Next prompt" disabled={zoomed === session.prompts.length - 1} onClick={() => onZoom(zoomed === null ? 0 : zoomed + 1)}>
                ▸
              </button>
            </>
          )}
        </div>
      </div>
      <div ref={box} className="drill-scroll-x">
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          className={`drill-tl-svg${hit !== null ? ' is-pointing' : ''}`}
          role="img"
          aria-label="Timeline of the session"
          onPointerMove={onMove}
          onPointerLeave={() => {
            setHit(null);
            tip.hide();
          }}
          onClick={onClick}
        >
          <Marks marks={marks} prompts={prompts} bands={bands} scale={scale} width={width} zoomed={zoomed !== null} activation={activation} lit={lit} selected={selected} />
          {hovered !== null && hoveredRow !== null && (
            <rect x={hovered.x1 - 3} y={hoveredRow.y - 2} width={Math.max(6, hovered.x2 - hovered.x1 + 6)} height={hoveredRow.h + 4} className="drill-hover" />
          )}
        </svg>
      </div>
      <div className="drill-legend">
        <span><i className="drill-sw-main" />Model call, main thread</span>
        <span><i className="drill-sw-other" />Model call, subagent or side request</span>
        <span><i className="drill-sw-sub" />Subagent at work</span>
        <span><i className="drill-sw-tool" />Tool call</span>
        <span><i className="drill-sw-wait" />Waiting for your OK</span>
        <span><i className="drill-sw-hook" />Hook</span>
        <span><i className="drill-sw-force" />Skill in force</span>
        <span><i className="drill-sw-fail" />Failed</span>
        <span><i className="drill-sw-warn" />Rejected or blocked</span>
      </div>
      <SessionTip tip={tip.tip} />
    </section>
  );
}
