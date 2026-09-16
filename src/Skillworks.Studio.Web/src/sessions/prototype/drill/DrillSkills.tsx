// PROTOTYPE — throwaway. Variant A's skill calls: one activation at a time, cycled with the buttons or ← and →.

import { useEffect, useMemo, useRef, type PointerEvent } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import { SessionTip, useTip } from '../SessionTip';
import { describe, foldScale, format, lanesOf, startOf, type Activation, type Lane } from '../sessionMeasures';
import { useWidth } from './useDrillSession';

const strips: { key: string; label: string; lanes: Lane[] }[] = [
  { key: 'main', label: 'Model · main', lanes: ['main'] },
  { key: 'other', label: 'Model · other', lanes: ['other', 'subagent'] },
  { key: 'tools', label: 'Tools', lanes: ['shell', 'edit', 'read', 'tool'] },
  { key: 'hook', label: 'Hooks', lanes: ['hook'] },
  { key: 'fault', label: 'Faults', lanes: ['fault'] },
];
const stripLeft = 92;
const stripRow = 16;

const base = (path: string) => path.split(/[\\/]/).pop() ?? path;

function stepLine(step: SessionStep): { tag: string; text: string; tone: string } {
  switch (step.kind) {
    case 'model':
      return {
        tag: step.thread === 'main' ? 'Model' : step.thread === 'subagent' ? 'Subagent model' : 'Side',
        text: step.said?.text ?? (step.said ? `Words withheld · ${step.said.length} characters` : `${format.tokens(step.outputTokens)} out · ${step.stopReason} · ${format.usd(step.costUsd)}`),
        tone: step.thread === 'main' ? 'is-model' : '',
      };
    case 'tool':
      return { tag: step.tool, text: step.summary, tone: step.ok ? '' : 'is-fail' };
    case 'subagent':
      return { tag: 'Subagent', text: `${step.agentType} · ${step.description}`, tone: '' };
    case 'modelError':
      return { tag: `API ${step.status}`, text: step.message, tone: 'is-fail' };
    case 'rejected':
      return { tag: 'Rejected', text: step.summary, tone: 'is-warn' };
    case 'skill':
      return { tag: 'Skill', text: step.skill, tone: '' };
    case 'hook':
      return { tag: 'Hook', text: step.hook, tone: '' };
    case 'prompt':
      return { tag: 'Prompt', text: step.said.text ?? 'Words withheld', tone: '' };
  }
}

export function DrillSkills({
  session,
  activations,
  index,
  onIndex,
  onOpen,
}: {
  session: Session;
  activations: Activation[];
  index: number;
  onIndex: (index: number) => void;
  onOpen: (stepId: string) => void;
}) {
  const tip = useTip();
  const box = useRef<HTMLDivElement>(null);
  const width = Math.max(300, useWidth(box, 520));
  const current = activations[index] ?? null;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, select, [contenteditable]') || event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return;
      if (activations.length === 0) return;
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        onIndex((index - 1 + activations.length) % activations.length);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        onIndex((index + 1) % activations.length);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [activations.length, index, onIndex]);

  const strip = useMemo(() => {
    if (current === null) return null;
    const scale = foldScale(
      current.steps.map((step) => [Math.max(current.startMs, startOf(step)), step.at]),
      stripLeft,
      width - 8,
      90 * 1000,
    );
    const marks = current.steps.flatMap((step) =>
      lanesOf(step).flatMap((lane) => {
        const row = strips.findIndex((each) => each.lanes.includes(lane));
        if (row < 0) return [];
        const point = lane === 'fault' || step.ms === 0;
        return [{ row, step, x1: scale.map(point ? step.at : Math.max(current.startMs, startOf(step))), x2: scale.map(step.at), point, lane }];
      }),
    );
    return { scale, marks };
  }, [current, width]);

  if (current === null) {
    return (
      <section className="drill-frame drill-skills" aria-labelledby="drill-skills-title">
        <div className="drill-frame-head">
          <h2 id="drill-skills-title">Skill calls</h2>
        </div>
        <p className="drill-empty">No skill fired in this session.</p>
      </section>
    );
  }

  const listed = current.steps.filter((step) => step.kind !== 'hook');
  const height = strips.length * stripRow + 8;

  return (
    <section className="drill-frame drill-skills" aria-labelledby="drill-skills-title">
      <div className="drill-frame-head">
        <h2 id="drill-skills-title">Skill calls</h2>
        <span className="drill-sub">Each time a skill fired, and what ran until the next one fired or the prompt ended. ← and → cycle.</span>
        <div className="drill-cycle">
          <button type="button" className="drill-key" aria-label="Previous skill call" onClick={() => onIndex((index - 1 + activations.length) % activations.length)}>
            ◂
          </button>
          <span className="drill-fig" aria-live="polite">
            {index + 1} of {activations.length}
          </span>
          <button type="button" className="drill-key" aria-label="Next skill call" onClick={() => onIndex((index + 1) % activations.length)}>
            ▸
          </button>
        </div>
      </div>

      <div className="drill-pills" role="group" aria-label="Skill calls">
        {activations.map((each) => (
          <button key={each.index} type="button" className="drill-pill" aria-pressed={each.index === index} onClick={() => onIndex(each.index)}>
            <span className="drill-faint">P{each.prompt.index + 1}</span> {each.step.skill}
            {each.failedTools > 0 && <span className="drill-bad"> ◆{each.failedTools}</span>}
          </button>
        ))}
      </div>

      <div className="drill-skill-card">
        <div className="drill-skill-facts">
          <p className="drill-skill-name">{current.step.skill}</p>
          <p className="drill-skill-why">
            {format.trigger(current.step.trigger)}
            {current.calledFrom !== null && <> · called from <b>{current.calledFrom}</b></>} · {current.step.source}
          </p>
          <p className="drill-fine">
            Prompt {current.prompt.index + 1} · {format.clock(current.startMs, true)} to {format.clock(current.endMs, true)} · {format.duration(current.endMs - current.startMs)}
          </p>
          <dl className="drill-mini-totals">
            <div className="is-hero">
              <dt>Cost</dt>
              <dd>{format.usd(current.costUsd)}</dd>
            </div>
            <div>
              <dt>Model calls</dt>
              <dd>{current.modelCalls}</dd>
            </div>
            <div>
              <dt>Tool calls</dt>
              <dd>{current.toolCalls}</dd>
            </div>
            <div className={current.failedTools > 0 ? 'is-bad' : ''}>
              <dt>Failed</dt>
              <dd>{current.failedTools}</dd>
            </div>
            <div>
              <dt>Subagents</dt>
              <dd>{current.subagents}</dd>
            </div>
          </dl>
          <h3 className="drill-micro">Files edited</h3>
          {current.files.length === 0 ? (
            <p className="drill-fine">None.</p>
          ) : (
            <ul className="drill-files">
              {current.files.slice(0, 6).map((file) => (
                <li key={file.file} title={file.file}>
                  <span>{base(file.file)}</span>
                  <span className={`drill-fig${file.edits >= 6 ? ' drill-warn-text' : ''}`}>{file.edits}×</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="drill-skill-inside">
          <div ref={box}>
            {strip !== null && (
              <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="What ran while this skill was in force" onPointerLeave={tip.hide}>
                {strips.map((row, rowIndex) => (
                  <g key={row.key}>
                    <text x={stripLeft - 8} y={rowIndex * stripRow + 4 + stripRow / 2 + 3} textAnchor="end" className="drill-t-label">
                      {row.label}
                    </text>
                    <rect x={stripLeft} y={rowIndex * stripRow + 4 + stripRow / 2 - 0.5} width={width - stripLeft - 8} height={1} className="drill-track" />
                  </g>
                ))}
                {strip.scale.gaps.map((gap) => (
                  <line key={gap.fromMs} x1={gap.x} x2={gap.x} y1={2} y2={height - 2} className="drill-fold-one" />
                ))}
                {strip.marks.map((mark) => {
                  const y = mark.row * stripRow + 4;
                  const tone = mark.lane === 'fault' ? 'fail' : mark.step.kind === 'model' ? (mark.step.thread === 'main' ? 'main' : 'other') : mark.step.kind === 'subagent' ? 'sub' : mark.step.kind === 'hook' ? 'hook' : 'tool';
                  const events = {
                    onPointerMove: (event: PointerEvent) => tip.show(describe(mark.step, session), event),
                    onClick: () => onOpen(mark.step.id),
                  };
                  if (mark.point) {
                    const cy = y + stripRow / 2;
                    return <path key={`${mark.step.id}-${mark.lane}`} d={`M${mark.x1} ${cy - 5}L${mark.x1 + 5} ${cy}L${mark.x1} ${cy + 5}L${mark.x1 - 5} ${cy}Z`} className={`drill-mk drill-m-${tone} drill-click`} {...events} />;
                  }
                  return (
                    <rect
                      key={`${mark.step.id}-${mark.lane}`}
                      x={mark.x1}
                      y={y + 3}
                      width={Math.max(2, mark.x2 - mark.x1)}
                      height={stripRow - 6}
                      rx={1}
                      className={`drill-mk drill-m-${tone} drill-click`}
                      strokeWidth={6}
                      stroke="transparent"
                      {...events}
                    />
                  );
                })}
              </svg>
            )}
          </div>
          <ol className="drill-steps">
            {listed.map((step) => {
              const line = stepLine(step);
              return (
                <li key={step.id} className={line.tone}>
                  <button type="button" onClick={() => onOpen(step.id)}>
                    <time>{format.clock(step.at, true)}</time>
                    <span className="drill-steps-tag">{line.tag}</span>
                    <span className="drill-steps-text">{line.text}</span>
                    <span className="drill-fig drill-faint">{step.ms > 0 ? format.duration(step.ms) : ''}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
      <SessionTip tip={tip.tip} />
    </section>
  );
}
