// PROTOTYPE — throwaway. The Trace tab: the prompt's span tree as a waterfall, and everything known about the span
// that was clicked. One prompt is one trace, so the tree always starts at the prompt.

import { memo, useEffect, useMemo, useRef } from 'react';
import type { ModelStep, Session, SessionStep, ToolStep } from '../sessionModel';
import { describe, format, startOf, traceFor, type SpanName } from '../sessionMeasures';
import { settings, type Range, windowAround } from './scrubRange';
import { ScrubToolContent, ScrubWords } from './ScrubWords';

const spanClass: Record<SpanName, string> = {
  interaction: 'is-interaction',
  llm_request: 'is-llm',
  tool: 'is-tool',
  'tool.blocked_on_user': 'is-wait',
  'tool.execution': 'is-run',
  hook: 'is-hook',
  subagent: 'is-agent',
  error: 'is-failed',
};

function SpanDetail({ session, step, onSelect, onRange }: { session: Session; step: SessionStep; onSelect: (id: string) => void; onRange: (range: Range) => void }) {
  const description = describe(step, session);
  const toolsByUse = useMemo(() => new Map(session.steps.filter((each): each is ToolStep => each.kind === 'tool').map((tool) => [tool.toolUseId, tool])), [session]);
  const askedBy = step.kind === 'tool' ? session.steps.find((each): each is ModelStep => each.kind === 'model' && each.toolUseIds.includes(step.toolUseId)) : undefined;
  const spanNameOf = step.kind === 'model' ? 'claude_code.llm_request' : step.kind === 'tool' || step.kind === 'rejected' ? 'claude_code.tool' : step.kind === 'hook' ? 'claude_code.hook' : step.kind === 'subagent' ? 'claude_code.subagent' : step.kind === 'prompt' ? 'claude_code.interaction' : step.kind;

  return (
    <div className={`scrub-span-detail${description.tone ? ` is-${description.tone}` : ''}`}>
      <div className="scrub-span-head">
        <p className="scrub-micro">{spanNameOf}</p>
        <h3>{description.title}</h3>
        <p className="scrub-span-when">
          {format.day(startOf(step))} {description.when}
        </p>
        <button type="button" className="scrub-small-button" onClick={() => onRange(windowAround(startOf(step), step.at, session))}>
          Brush the timeline to it
        </button>
      </div>

      {description.rows.length > 0 && (
        <dl className="scrub-attributes">
          {description.rows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
          <div>
            <dt>Span</dt>
            <dd>{step.id}</dd>
          </div>
          {step.agent !== null && (
            <div>
              <dt>Agent id</dt>
              <dd>{step.agent}</dd>
            </div>
          )}
          {step.kind === 'model' && (
            <div>
              <dt>Request</dt>
              <dd>{step.requestId}</dd>
            </div>
          )}
        </dl>
      )}

      {step.kind === 'prompt' && (
        <>
          <p className="scrub-micro">What was typed</p>
          <ScrubWords said={step.said} setting={settings.prompts} />
        </>
      )}

      {step.kind === 'model' && (
        <>
          <p className="scrub-micro">What the model wrote</p>
          {step.said === null ? <p className="scrub-quiet">No text in this reply. It only asked for tools.</p> : <ScrubWords said={step.said} setting={settings.responses} />}
          <p className="scrub-quiet">Thinking is never sent.</p>
          {step.toolUseIds.length > 0 && (
            <>
              <p className="scrub-micro">It asked for</p>
              <ul className="scrub-link-list">
                {step.toolUseIds.map((id) => {
                  const tool = toolsByUse.get(id);
                  return (
                    <li key={id}>
                      {tool ? (
                        <button type="button" className={`scrub-link${tool.ok ? '' : ' is-failed'}`} onClick={() => onSelect(tool.id)}>
                          {tool.tool} · {tool.summary}
                        </button>
                      ) : (
                        <span className="scrub-quiet">A tool call with no result yet</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </>
      )}

      {step.kind === 'tool' && (
        <>
          {askedBy && (
            <p className="scrub-quiet">
              Asked for by{' '}
              <button type="button" className="scrub-link" onClick={() => onSelect(askedBy.id)}>
                a model call at {format.clock(askedBy.at, true)}
              </button>
            </p>
          )}
          {!step.ok && <p className="scrub-error">{step.errorType} · {step.error}</p>}
          <ScrubToolContent tool={step} />
        </>
      )}

      {step.kind === 'rejected' && <pre className="scrub-pre">{step.summary}</pre>}
      {step.kind === 'modelError' && <p className="scrub-error">{step.message}</p>}
      {step.kind === 'subagent' && <p className="scrub-quiet">Its own model calls and tools sit under it in the tree.</p>}
    </div>
  );
}

export const ScrubTrace = memo(function ScrubTrace({
  session,
  stepId,
  range,
  onSelect,
  onRange,
}: {
  session: Session;
  stepId: string | null;
  range: Range | null;
  onSelect: (id: string) => void;
  onRange: (range: Range) => void;
}) {
  const trace = useMemo(() => (stepId === null ? null : traceFor(session, stepId)), [session, stepId]);
  const list = useRef<HTMLOListElement>(null);
  const step = stepId === null ? undefined : session.steps.find((each) => each.id === stepId);

  useEffect(() => {
    if (stepId === null || trace === null) return;
    list.current?.children[trace.rows.findIndex((row) => row.id === stepId)]?.scrollIntoView({ block: 'center' });
  }, [stepId, trace]);

  if (trace === null || step === undefined) {
    return (
      <div className="scrub-dock-empty">
        <p>Click any mark on the timeline to open its trace.</p>
        <p className="scrub-quiet">A trace is the tree of steps for one prompt. The clicked step is marked in it, with its details on the right.</p>
      </div>
    );
  }

  // The waterfall follows the brush too: a long prompt's bars are slivers until the brush narrows the time they share.
  const zoomed = range !== null && range[1] > trace.startMs && range[0] < trace.endMs;
  const domainStart = zoomed ? Math.max(trace.startMs, range[0]) : trace.startMs;
  const domainEnd = zoomed ? Math.min(trace.endMs, range[1]) : trace.endMs;
  const total = Math.max(1, domainEnd - domainStart);

  return (
    <div className="scrub-trace">
      <div className="scrub-waterfall">
        <div className="scrub-waterfall-head">
          <span className="scrub-micro">
            Prompt {trace.prompt.index + 1} · {trace.rows.length} spans{zoomed ? ' · zoomed to the brush' : ''}
          </span>
          <span className="scrub-axis-row">
            <span>{format.clock(domainStart, true)}</span>
            <span>{format.duration(total)}</span>
            <span>{format.clock(domainEnd, true)}</span>
          </span>
        </div>
        <ol className="scrub-spans" ref={list}>
          {trace.rows.map((row) => {
            const target = row.step?.id ?? row.id.split(':')[0];
            const chosen = row.id === stepId;
            const outside = row.endMs < domainStart || row.startMs > domainEnd;
            const offset = Math.max(0, ((row.startMs - domainStart) / total) * 100);
            const end = Math.min(100, ((row.endMs - domainStart) / total) * 100);
            const width = Math.max(0.3, end - offset);
            return (
              <li key={row.id} className={`${chosen ? 'is-chosen' : ''}${row.failed ? ' is-failed' : ''}${outside ? ' is-outside' : ''}`}>
                <button type="button" onClick={() => onSelect(target)} title={row.label}>
                  <span className="scrub-span-name" style={{ paddingLeft: `${Math.min(row.depth, 6) * 12 + 4}px` }}>
                    <b>{row.name}</b> {row.label}
                  </span>
                  <span className="scrub-span-track">
                    {!outside && <i className={`${spanClass[row.name]}${row.failed ? ' is-failed' : ''}`} style={{ left: `${Math.min(99.7, offset)}%`, width: `${Math.min(100 - offset, width)}%` }} />}
                  </span>
                  <span className="scrub-span-ms">{format.duration(row.endMs - row.startMs)}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
      <SpanDetail session={session} step={step} onSelect={onSelect} onRange={onRange} />
    </div>
  );
});
