// PROTOTYPE — throwaway. One prompt as a chapter: what was typed, a strip of the work, what the model said, the answer.

import { memo, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import type { ModelStep, Session, SessionStep, SkillStep, ToolStep } from '../sessionModel';
import { describe, foldScale, format, startOf, type Activation, type Description, type Exchange } from '../sessionMeasures';
import { StoryTrace } from './StoryTrace';
import { settings, ToolContent, Words } from './StoryWords';
import { useStoryBox } from './useStoryBox';

type ShowTip = (description: Description, event: { clientX: number; clientY: number }, hint?: string | null) => void;

export interface PromptFacts {
  costUsd: number;
  calls: number;
  tools: number;
  failed: number;
}

const isFault = (step: SessionStep) =>
  (step.kind === 'tool' && !step.ok) || step.kind === 'modelError' || step.kind === 'rejected' || (step.kind === 'hook' && step.blocking > 0);

const tracks: { key: string; label: string; holds: (step: SessionStep) => boolean }[] = [
  { key: 'skill', label: 'Skills', holds: (step) => step.kind === 'skill' },
  { key: 'main', label: 'Model', holds: (step) => step.kind === 'model' && step.thread === 'main' },
  { key: 'other', label: 'Other', holds: (step) => step.kind === 'model' && step.thread !== 'main' },
  { key: 'agent', label: 'Agents', holds: (step) => step.kind === 'subagent' },
  { key: 'tool', label: 'Tools', holds: (step) => step.kind === 'tool' && step.family !== 'agent' },
  { key: 'hook', label: 'Hooks', holds: (step) => step.kind === 'hook' },
  { key: 'fault', label: 'Faults', holds: isFault },
];

const trackHeight = 10;
const trackGap = 3;
const stripLeft = 50;

function WorkStrip({
  session,
  steps,
  focusStepId,
  onOpen,
  showTip,
  hideTip,
}: {
  session: Session;
  steps: SessionStep[];
  focusStepId: string | null;
  onOpen: (step: SessionStep) => void;
  showTip: ShowTip;
  hideTip: () => void;
}) {
  const [ref, box] = useStoryBox<HTMLDivElement>(700, 80);
  const [hover, setHover] = useState<string | null>(null);
  const width = Math.max(320, box.width);
  const top = 2;

  // A question with two model calls needs one row, not seven empty ones.
  const drawn = useMemo(() => {
    const scale = foldScale(
      steps.filter((step) => step.kind !== 'prompt').map((step) => [startOf(step), step.at] as [number, number]),
      stripLeft,
      width - 6,
    );
    const shown = tracks.filter((track) => track.key === 'main' || steps.some(track.holds));
    const marks = shown.map((track) =>
      steps
        .filter(track.holds)
        .map((step) => ({ step, x1: scale.map(startOf(step)), x2: scale.map(step.at) }))
        .toSorted((a, b) => a.x1 - b.x1),
    );
    return { scale, marks, shown };
  }, [steps, width]);

  const axisY = top + drawn.shown.length * (trackHeight + trackGap) + 2;
  const height = axisY + 14;

  const find = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const index = Math.floor((y - top) / (trackHeight + trackGap));
    if (index < 0 || index >= drawn.shown.length) return null;
    let best: SessionStep | null = null;
    let distance = 7;
    for (const mark of drawn.marks[index]) {
      const away = x < mark.x1 ? mark.x1 - x : x > Math.max(mark.x2, mark.x1 + 2) ? x - Math.max(mark.x2, mark.x1 + 2) : 0;
      if (away < distance || (away === 0 && best !== null && mark.x2 - mark.x1 < 2)) {
        distance = away;
        best = mark.step;
      }
    }
    return best;
  };

  const first = drawn.scale.segments[0]?.[0] ?? 0;
  const last = drawn.scale.segments[drawn.scale.segments.length - 1]?.[1] ?? 0;

  return (
    <div ref={ref} className="story-strip">
      <svg
        width={width}
        height={height}
        role="img"
        aria-label="The work in this prompt, one row per kind of step"
        onPointerMove={(event) => {
          const step = find(event);
          setHover(step?.id ?? null);
          if (step === null) hideTip();
          else showTip(describe(step, session), event);
        }}
        onPointerLeave={() => {
          setHover(null);
          hideTip();
        }}
        onClick={(event) => {
          const step = find(event);
          if (step !== null) onOpen(step);
        }}
        className={hover !== null ? 'is-pointing' : undefined}
      >
        {drawn.shown.map((track, index) => {
          const y = top + index * (trackHeight + trackGap);
          return (
            <g key={track.key}>
              <text x={stripLeft - 6} y={y + trackHeight - 1} textAnchor="end" className="story-svg-label">
                {track.label}
              </text>
              <rect x={stripLeft} y={y + trackHeight / 2 - 0.5} width={width - stripLeft - 6} height={1} className="story-track" />
            </g>
          );
        })}

        {drawn.scale.gaps.map((gap) => (
          <g key={gap.x}>
            <line x1={gap.x} x2={gap.x} y1={top} y2={axisY} className="story-gapline" />
            <text x={gap.x} y={axisY + 11} textAnchor="middle" className="story-svg-faint">
              {format.short(gap.toMs - gap.fromMs)}
            </text>
          </g>
        ))}

        {drawn.marks.map((marks, index) => {
          const track = drawn.shown[index];
          const y = top + index * (trackHeight + trackGap);
          return marks.map(({ step, x1, x2 }) => {
            const on = step.id === focusStepId || step.id === hover;
            if (track.key === 'fault') {
              const cx = x2;
              const cy = y + trackHeight / 2;
              return <path key={step.id} d={`M${cx} ${cy - 4.5}L${cx + 4.5} ${cy}L${cx} ${cy + 4.5}L${cx - 4.5} ${cy}Z`} className={`story-mark ${step.kind === 'rejected' || step.kind === 'hook' ? 'is-warned' : 'is-failed'}${on ? ' is-on' : ''}`} />;
            }
            if (track.key === 'skill') {
              return <path key={step.id} d={`M${x2} ${y + trackHeight + 1}V${y - 1}L${x2 + 6} ${y + 2}L${x2} ${y + 5}`} className={`story-mark is-skill${on ? ' is-on' : ''}`} />;
            }
            const tone =
              step.kind === 'model' ? (step.thread === 'main' ? 'is-main' : 'is-other') : step.kind === 'subagent' ? 'is-agent' : step.kind === 'hook' ? 'is-hook' : step.kind === 'tool' && !step.ok ? 'is-failed' : 'is-tool';
            return <rect key={step.id} x={x1} y={y + 1} width={Math.max(1.5, x2 - x1)} height={trackHeight - 2} rx={1} className={`story-mark ${tone}${on ? ' is-on' : ''}`} />;
          });
        })}

        <text x={stripLeft} y={axisY + 11} className="story-svg-axis">
          {format.clock(first + 1, true)}
        </text>
        <text x={width - 6} y={axisY + 11} textAnchor="end" className="story-svg-axis">
          {format.clock(last, true)}
        </text>
      </svg>
    </div>
  );
}

// ---- the words, with tool calls folded between them ----

type Item =
  | { kind: 'skill'; step: SkillStep; act: Activation | undefined }
  | { kind: 'said'; call: ModelStep }
  | { kind: 'tools'; id: string; tools: ToolStep[] };

const base = (path: string) => path.split(/[\\/]/).pop() ?? path;

function toolKey(tool: ToolStep) {
  if (tool.family === 'shell') return `${tool.summary.length > 46 ? `${tool.summary.slice(0, 44)}…` : tool.summary}`;
  if (tool.tool === 'Grep') return `Grep ${tool.summary.split('  in ')[0]}`;
  if (tool.family === 'agent') return `Agent ${tool.summary.split(':')[0]}`;
  if (tool.tool === 'WebFetch' || tool.tool === 'WebSearch') return `${tool.tool} ${tool.summary.replace(/^https?:\/\//, '').slice(0, 40)}`;
  if (tool.family === 'read' || tool.family === 'edit') return `${tool.tool} ${base(tool.summary)}`;
  return `${tool.tool} ${tool.summary}`;
}

function foldSummary(tools: ToolStep[]) {
  const groups = new Map<string, { count: number; failed: number }>();
  for (const tool of tools) {
    const key = toolKey(tool);
    const group = groups.get(key) ?? { count: 0, failed: 0 };
    group.count += 1;
    if (!tool.ok) group.failed += 1;
    groups.set(key, group);
  }
  const ordered = [...groups.entries()].toSorted((a, b) => b[1].count - a[1].count);
  const shown = ordered.slice(0, 3).map(([key, group]) => `${group.count} × ${key}${group.failed > 0 ? `, ${group.failed} failed` : ''}`);
  return { text: shown.join(' · '), more: ordered.length - 3, failed: tools.filter((tool) => !tool.ok).length };
}

function ToolFold({ tools, onOpen }: { tools: ToolStep[]; onOpen: (step: SessionStep) => void }) {
  const summary = foldSummary(tools);
  const start = Math.min(...tools.map(startOf));
  const end = Math.max(...tools.map((tool) => tool.at));

  return (
    <details className={`story-fold${summary.failed > 0 ? ' has-failed' : ''}`}>
      <summary>
        <span className="story-fold-count">{tools.length} tool call{tools.length === 1 ? '' : 's'}</span>
        <span className="story-fold-text">
          {summary.text}
          {summary.more > 0 && <span className="story-faint"> · +{summary.more} more</span>}
        </span>
        <span className="story-fig story-faint">{format.duration(end - start)}</span>
      </summary>
      <ol className="story-fold-list">
        {tools.map((tool) => (
          <li key={tool.id}>
            <details className={tool.ok ? undefined : 'is-failed'}>
              <summary>
                <span className="story-tool-mark" aria-hidden="true">
                  {tool.ok ? '✓' : '◆'}
                </span>
                <span className="story-tool-name">{tool.tool}</span>
                <code>{tool.summary}</code>
                <span className="story-fig story-faint">
                  {tool.waitedMs > 0 && `waited ${format.duration(tool.waitedMs)} · `}
                  {format.duration(tool.ms - tool.waitedMs)}
                </span>
              </summary>
              <ToolContent step={tool} />
              <button type="button" className="story-link" onClick={() => onOpen(tool)}>
                Show in the trace →
              </button>
            </details>
          </li>
        ))}
      </ol>
    </details>
  );
}

export const StoryChapter = memo(function StoryChapter({
  session,
  exchange,
  steps,
  facts,
  acts,
  currentActivation,
  focusStepId,
  last,
  now,
  onOpen,
  onClose,
  onChooseActivation,
  showTip,
  hideTip,
}: {
  session: Session;
  exchange: Exchange;
  steps: SessionStep[];
  facts: PromptFacts;
  acts: Activation[];
  currentActivation: number | null;
  focusStepId: string | null;
  last: boolean;
  now: number;
  onOpen: (step: SessionStep) => void;
  onClose: () => void;
  onChooseActivation: (index: number | null) => void;
  showTip: ShowTip;
  hideTip: () => void;
}) {
  const { span, prompt, answer } = exchange;
  const traceRef = useRef<HTMLDivElement>(null);
  const opened = useRef(false);

  const items = useMemo(() => {
    const byStep = new Map(acts.map((act) => [act.step.id, act]));
    const timed: { at: number; order: number; item: Item | ModelStep }[] = [
      ...exchange.skills.map((step) => ({ at: step.at, order: 0, item: { kind: 'skill', step, act: byStep.get(step.id) } as Item })),
      ...exchange.turns.filter((turn) => turn.call !== answer).map((turn) => ({ at: startOf(turn.call), order: 1, item: turn.call })),
    ].toSorted((a, b) => a.at - b.at || a.order - b.order);

    const tools = new Map(exchange.turns.map((turn) => [turn.call.id, turn.tools]));
    const out: Item[] = [];
    let fold: ToolStep[] | null = null;

    for (const { item } of timed) {
      if ('kind' in item && item.kind === 'skill') {
        fold = null;
        out.push(item);
        continue;
      }
      const call = item as ModelStep;
      if (call.said !== null) {
        fold = null;
        out.push({ kind: 'said', call });
      }
      const called = tools.get(call.id) ?? [];
      if (called.length === 0) continue;
      if (fold === null) {
        fold = [];
        out.push({ kind: 'tools', id: call.id, tools: fold });
      }
      fold.push(...called);
    }
    return out;
  }, [exchange, acts, answer]);

  // Only a trace opened after the chapter is on screen pulls the page; the first landing is the session's job.
  useEffect(() => {
    if (!opened.current) {
      opened.current = true;
      return;
    }
    if (focusStepId !== null) traceRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [focusStepId]);

  const lastAt = steps.reduce((latest, step) => Math.max(latest, step.at), span.startMs);

  return (
    <section className="story-chapter" id={`story-chapter-${span.index}`} data-story-prompt={span.index} aria-label={`Prompt ${span.index + 1}`}>
      <header className="story-chapter-head">
        <b>P{span.index + 1}</b>
        <span>{format.clock(span.startMs)}</span>
        <span>{format.short(span.endMs - span.startMs)}</span>
        <span>{format.usd(facts.costUsd)}</span>
        <span>
          {facts.calls} calls · {facts.tools} tools
        </span>
        {facts.failed > 0 && <span className="story-bad">◆ {facts.failed} failed</span>}
        {prompt.command !== null && <span className="story-badge">/{prompt.command}</span>}
      </header>

      <div className="story-typed">
        <span className="story-who">You</span>
        <Words said={prompt.said} setting={settings.prompts} tone="typed" />
      </div>

      <WorkStrip session={session} steps={steps} focusStepId={focusStepId} onOpen={onOpen} showTip={showTip} hideTip={hideTip} />

      {focusStepId !== null && (
        <div ref={traceRef} id="story-trace">
          <StoryTrace key={span.index} session={session} stepId={focusStepId} onSelect={onOpen} onClose={onClose} />
        </div>
      )}

      <ol className="story-flow">
        {items.map((item) =>
          item.kind === 'skill' ? (
            <li key={item.step.id} id={item.act !== undefined ? `story-activation-${item.act.index}` : undefined} className={`story-divider${item.act !== undefined && item.act.index === currentActivation ? ' is-on' : ''}`}>
              <button type="button" onClick={() => item.act !== undefined && onChooseActivation(item.act.index === currentActivation ? null : item.act.index)}>
                <span className="story-micro">Skill</span>
                <b>{item.step.skill}</b>
                <span>{format.trigger(item.step.trigger)}</span>
                {item.act?.calledFrom && <span>from {item.act.calledFrom}</span>}
                <span className="story-fig">{format.clock(item.step.at, true)}</span>
                {item.act !== undefined && (
                  <span className="story-fig story-faint">
                    {format.duration(item.act.endMs - item.act.startMs)} · {format.usd(item.act.costUsd)}
                  </span>
                )}
              </button>
            </li>
          ) : item.kind === 'said' && item.call.said !== null ? (
            <li key={item.call.id} className="story-narration">
              <Words said={item.call.said} setting={settings.responses} tone="aside" />
            </li>
          ) : item.kind === 'tools' ? (
            <li key={`tools-${item.id}`}>
              <ToolFold tools={item.tools} onOpen={onOpen} />
            </li>
          ) : null,
        )}
      </ol>

      {answer !== null && answer.said !== null ? (
        <div className="story-answer">
          <span className="story-who">
            Claude · {format.clock(answer.at)} · {format.model(answer.model)}
          </span>
          <Words said={answer.said} setting={settings.responses} tone="written" />
        </div>
      ) : last && session.running ? (
        <p className="story-running">
          <span className="story-live-dot" aria-hidden="true" /> Still working · last step {format.ago(lastAt, now)}
        </p>
      ) : null}
    </section>
  );
});
