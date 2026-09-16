// PROTOTYPE — throwaway. The Skill calls tab: every activation in the session, and what happened inside the chosen one.
// Choosing one also brushes the timeline to its window, so the lanes above show the same stretch.

import { memo, useEffect, useRef } from 'react';
import type { ModelStep, Session, SessionStep, ToolStep } from '../sessionModel';
import { describe, format, startOf, type Activation } from '../sessionMeasures';
import type { useTip } from '../SessionTip';
import { settings } from './scrubRange';
import { ScrubWords } from './ScrubWords';

type Tip = Pick<ReturnType<typeof useTip>, 'show' | 'hide'>;

const stripLanes = ['model', 'tool', 'hook', 'fault'] as const;

function laneFor(step: SessionStep): (typeof stripLanes)[number] | null {
  if (step.kind === 'model') return 'model';
  if (step.kind === 'tool') return step.ok ? 'tool' : 'fault';
  if (step.kind === 'hook') return 'hook';
  if (step.kind === 'modelError' || step.kind === 'rejected') return 'fault';
  return null;
}

function Strip({ activation, session, tip, onStep }: { activation: Activation; session: Session; tip: Tip; onStep: (id: string) => void }) {
  const width = 1000;
  const rowHeight = 12;
  const span = Math.max(1, activation.endMs - activation.startMs);
  const x = (ms: number) => ((ms - activation.startMs) / span) * width;

  return (
    <svg className="scrub-strip" viewBox={`0 0 ${width} ${stripLanes.length * (rowHeight + 3)}`} preserveAspectRatio="none" role="img" aria-label="Steps inside this skill call">
      {stripLanes.map((lane, index) => (
        <line key={lane} x1={0} x2={width} y1={index * (rowHeight + 3) + rowHeight / 2} y2={index * (rowHeight + 3) + rowHeight / 2} className="scrub-track" />
      ))}
      {activation.steps.map((step) => {
        const lane = laneFor(step);
        if (lane === null) return null;
        const index = stripLanes.indexOf(lane);
        const x1 = x(Math.max(activation.startMs, startOf(step)));
        const x2 = x(Math.min(activation.endMs, step.at));
        const className = step.kind === 'model' ? (step.thread === 'main' ? 'is-main' : 'is-sub') : lane === 'fault' ? 'is-failed' : lane === 'hook' ? 'is-hook' : 'is-tool';
        return (
          <rect
            key={step.id}
            x={x1}
            y={index * (rowHeight + 3) + 2}
            width={Math.max(3, x2 - x1)}
            height={rowHeight - 4}
            className={`scrub-mark ${className}`}
            onPointerMove={(event) => tip.show(describe(step, session), event)}
            onPointerLeave={() => tip.hide()}
            onClick={() => onStep(step.id)}
          />
        );
      })}
    </svg>
  );
}

export const ScrubSkills = memo(function ScrubSkills({
  session,
  activations,
  chosen,
  tip,
  onChoose,
  onStep,
}: {
  session: Session;
  activations: Activation[];
  chosen: number | null;
  tip: Tip;
  onChoose: (index: number) => void;
  onStep: (id: string) => void;
}) {
  const list = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (chosen === null) return;
    list.current?.children[chosen]?.scrollIntoView({ block: 'nearest' });
  }, [chosen]);

  if (activations.length === 0) {
    return (
      <div className="scrub-dock-empty">
        <p>No skill fired in this session.</p>
        <p className="scrub-quiet">Every model call here belongs to no skill.</p>
      </div>
    );
  }

  const activation = chosen === null ? null : activations[chosen];
  const count = activations.length;
  const tools = activation?.steps.filter((step): step is ToolStep => step.kind === 'tool') ?? [];
  const words = activation?.steps.filter((step): step is ModelStep => step.kind === 'model' && step.thread === 'main' && step.said !== null) ?? [];

  return (
    <div className="scrub-skills">
      <ol className="scrub-activations" ref={list}>
        {activations.map((each) => (
          <li key={each.index}>
            <button type="button" aria-pressed={each.index === chosen} onClick={() => onChoose(each.index)} className="scrub-activation">
              <span className="scrub-activation-name">
                <b>{each.index + 1}</b> {each.step.skill}
                {each.failedTools > 0 && <i className="scrub-fault-dot" aria-label={`${each.failedTools} failed`} />}
              </span>
              <span className="scrub-session-meta">
                {format.clock(each.startMs)} · {format.trigger(each.step.trigger)} · {format.short(each.endMs - each.startMs)} · {format.usd(each.costUsd)}
              </span>
            </button>
          </li>
        ))}
      </ol>

      {activation === null ? (
        <div className="scrub-dock-empty">
          <p>Pick a skill call, or press ← → to step through them.</p>
          <p className="scrub-quiet">The timeline brushes to the one you pick.</p>
        </div>
      ) : (
        <div className="scrub-activation-detail">
          <div className="scrub-activation-head">
            <button type="button" className="scrub-step" onClick={() => onChoose((activation.index - 1 + count) % count)} aria-label="Previous skill call">
              ◂
            </button>
            <span className="scrub-micro">
              {activation.index + 1} of {count}
            </span>
            <button type="button" className="scrub-step" onClick={() => onChoose((activation.index + 1) % count)} aria-label="Next skill call">
              ▸
            </button>
            <h3>{activation.step.skill}</h3>
            <span className="scrub-quiet">
              {format.trigger(activation.step.trigger)}
              {activation.calledFrom ? ` by ${activation.calledFrom}` : ''} · prompt {activation.prompt.index + 1} · {activation.step.source} · {format.clock(activation.startMs, true)} to {format.clock(activation.endMs, true)}
            </span>
          </div>

          <dl className="scrub-figures">
            <div>
              <dt>Ran for</dt>
              <dd>{format.duration(activation.endMs - activation.startMs)}</dd>
            </div>
            <div>
              <dt>Cost</dt>
              <dd>{format.usd(activation.costUsd)}</dd>
            </div>
            <div>
              <dt>Model calls</dt>
              <dd>{activation.modelCalls}</dd>
            </div>
            <div>
              <dt>Tool calls</dt>
              <dd>{activation.toolCalls}</dd>
            </div>
            <div className={activation.failedTools > 0 ? 'is-failed' : ''}>
              <dt>Failed</dt>
              <dd>{activation.failedTools}</dd>
            </div>
            <div>
              <dt>Subagents</dt>
              <dd>{activation.subagents}</dd>
            </div>
          </dl>

          <div className="scrub-strip-wrap">
            <span className="scrub-strip-labels" aria-hidden="true">
              <span>Model</span>
              <span>Tools</span>
              <span>Hooks</span>
              <span>Faults</span>
            </span>
            <Strip activation={activation} session={session} tip={tip} onStep={onStep} />
          </div>

          <div className="scrub-activation-columns">
            <div>
              <p className="scrub-micro">Files edited</p>
              {activation.files.length === 0 ? (
                <p className="scrub-quiet">None.</p>
              ) : (
                <ul className="scrub-files">
                  {activation.files.slice(0, 8).map((file) => (
                    <li key={file.file} className={file.edits >= 6 ? 'is-warned' : ''}>
                      <span title={file.file}>{file.file.split(/[\\/]/).pop()}</span>
                      <span>{file.edits}×</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="scrub-micro">What the model wrote</p>
              {words.length === 0 ? (
                <p className="scrub-quiet">Only tool calls, no text.</p>
              ) : (
                words.slice(-3).map((call) => call.said !== null && <ScrubWords key={call.id} said={call.said} setting={settings.responses} clip={420} />)
              )}
            </div>
            <div>
              <p className="scrub-micro">Tool calls · {tools.length}</p>
              <ol className="scrub-tool-list">
                {tools.map((tool) => (
                  <li key={tool.id}>
                    <button type="button" className={`scrub-link${tool.ok ? '' : ' is-failed'}`} onClick={() => onStep(tool.id)}>
                      <span className="scrub-tool-name">{tool.tool}</span> {tool.summary}
                    </button>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
