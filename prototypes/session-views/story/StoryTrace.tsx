// PROTOTYPE — throwaway. The trace of one prompt, opened in place under its work strip, with the chosen span's details.

import { useEffect, useMemo, useRef, useState } from 'react';
import type { Session, SessionStep } from '../sessionModel';
import { describe, format, traceFor, type TraceRow } from '../sessionMeasures';
import { settings, ToolContent, Words } from './StoryWords';

const tone = (row: TraceRow) => {
  if (row.failed) return 'is-failed';
  if (row.name === 'interaction' || row.name === 'subagent') return 'is-wash';
  if (row.name === 'llm_request') return row.step?.kind === 'model' && row.step.thread === 'main' ? 'is-main' : 'is-other';
  if (row.name === 'tool.blocked_on_user') return 'is-warned';
  if (row.name === 'hook' || row.name === 'tool.execution') return 'is-hook';
  return 'is-tool';
};

function Detail({ session, step, onSelect }: { session: Session; step: SessionStep; onSelect: (step: SessionStep) => void }) {
  const description = describe(step, session);
  const ids: [string, string][] = [
    ['Span', step.id],
    ['Parent', step.parent ?? 'none'],
  ];
  if (step.kind === 'model') ids.push(['Request', step.requestId], ['Query source', step.querySource], ['Effort', step.effort], ['Attempt', String(step.attempt)]);
  if (step.kind === 'tool') ids.push(['Tool use', step.toolUseId], ['Allowed by', step.allowedBy]);
  if (step.agent !== null) ids.push(['Agent', step.agent]);
  if (step.kind === 'subagent') ids.push(['Agent id', step.agentId]);

  const toolsCalled = step.kind === 'model' ? session.steps.filter((each) => each.kind === 'tool' && step.toolUseIds.includes(each.toolUseId)) : [];

  return (
    <div className={`story-detail${description.tone ? ` is-${description.tone}` : ''}`}>
      <p className="story-detail-title">{description.title}</p>
      <p className="story-fig story-faint">{description.when}</p>
      <dl>
        {[...description.rows, ...ids].map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>

      {step.kind === 'prompt' && (
        <>
          <p className="story-micro">What was typed</p>
          <Words said={step.said} setting={settings.prompts} tone="typed" />
        </>
      )}

      {step.kind === 'model' && (
        <>
          <p className="story-micro">What the model wrote</p>
          {step.said === null ? <p className="story-quiet">No text in this reply.</p> : <Words said={step.said} setting={settings.responses} tone="written" />}
          {toolsCalled.length > 0 && (
            <>
              <p className="story-micro">It asked for {toolsCalled.length} tool call{toolsCalled.length === 1 ? '' : 's'}</p>
              <ul className="story-detail-links">
                {toolsCalled.map((tool) => (
                  <li key={tool.id}>
                    <button type="button" className="story-link" onClick={() => onSelect(tool)}>
                      {tool.kind === 'tool' ? `${tool.tool} · ${tool.summary}` : tool.id}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
          <p className="story-quiet">Thinking never reaches telemetry.</p>
        </>
      )}

      {step.kind === 'tool' && <ToolContent step={step} />}
      {(step.kind === 'modelError' || step.kind === 'rejected') && description.code !== null && <pre className="story-pre is-failed">{description.code}</pre>}
    </div>
  );
}

export function StoryTrace({ session, stepId, onSelect, onClose }: { session: Session; stepId: string; onSelect: (step: SessionStep) => void; onClose: () => void }) {
  const trace = useMemo(() => traceFor(session, stepId), [session, stepId]);
  const list = useRef<HTMLOListElement>(null);

  const parents = useMemo(() => {
    const out: number[] = [];
    const stack: number[] = [];
    trace?.rows.forEach((row, index) => {
      while (stack.length > row.depth) stack.pop();
      out.push(stack.length > 0 ? stack[stack.length - 1] : -1);
      stack.push(index);
    });
    return out;
  }, [trace]);

  const focusIndex = trace?.rows.findIndex((row) => row.id === stepId) ?? -1;

  const path = useMemo(() => {
    const out = new Set<string>();
    for (let index = parents[focusIndex] ?? -1; index >= 0; index = parents[index]) out.add(trace?.rows[index].id ?? '');
    return out;
  }, [parents, focusIndex, trace]);

  // Subagents and each tool's own spans start folded, or a feature prompt is four hundred rows long. The path to the
  // chosen span opens by itself; a fold the reader clicks overrides that.
  const [toggled, setToggled] = useState<Map<string, boolean>>(() => new Map());
  const openById = (id: string) => toggled.get(id) ?? path.has(id);

  const hasChildren = useMemo(() => {
    const set = new Set<number>();
    for (const parent of parents) if (parent >= 0) set.add(parent);
    return set;
  }, [parents]);

  const shownRows = useMemo(() => {
    if (trace === null) return [];
    const visible: boolean[] = [];
    return trace.rows
      .map((row, index) => {
        const parent = parents[index];
        const parentOpen = parent === 0 || (parent > 0 && (toggled.get(trace.rows[parent].id) ?? path.has(trace.rows[parent].id)));
        visible[index] = parent < 0 || (visible[parent] && parentOpen);
        return { row, index };
      })
      .filter(({ index }) => visible[index]);
  }, [trace, parents, toggled, path]);

  const open = (index: number) => index === 0 || openById(trace?.rows[index].id ?? '');

  const scrolledTo = useRef<string | null>(null);
  useEffect(() => {
    if (scrolledTo.current === stepId) return;
    const container = list.current;
    const element = container?.querySelector<HTMLElement>('.is-focus');
    if (!element || !container) return;
    container.scrollTop = Math.max(0, element.offsetTop - container.clientHeight / 3);
    scrolledTo.current = stepId;
  });

  if (trace === null) return null;

  const focus = trace.rows[focusIndex]?.step ?? null;
  const total = Math.max(1, trace.endMs - trace.startMs);
  const select = (row: TraceRow, index: number) => {
    if (row.step !== null) onSelect(row.step);
    else {
      const parent = trace.rows[parents[index]]?.step;
      if (parent) onSelect(parent);
    }
  };

  return (
    <section className="story-trace" aria-label={`Trace of prompt ${trace.prompt.index + 1}`}>
      <header className="story-trace-head">
        <span className="story-micro">Trace</span>
        <b>Prompt {trace.prompt.index + 1}</b>
        <span className="story-fig">
          {trace.rows.length} spans · {format.duration(total)}
        </span>
        <span className="story-trace-legend">
          <span>
            <i className="is-main" />
            model, main
          </span>
          <span>
            <i className="is-other" />
            model, other
          </span>
          <span>
            <i className="is-tool" />
            tool
          </span>
          <span>
            <i className="is-warned" />
            waiting for OK
          </span>
          <span>
            <i className="is-hook" />
            hook, run
          </span>
          <span>
            <i className="is-failed" />
            failed
          </span>
        </span>
        <button type="button" className="story-close" onClick={onClose} aria-label="Close the trace">
          ×
        </button>
      </header>

      <div className="story-trace-body">
        <ol ref={list} className="story-waterfall">
          {shownRows.map(({ row, index }) => {
            const left = ((row.startMs - trace.startMs) / total) * 100;
            const width = Math.max(0.3, ((row.endMs - row.startMs) / total) * 100);
            const children = hasChildren.has(index);
            const isOpen = open(index);
            return (
              <li key={row.id} className={`${index === focusIndex ? 'is-focus' : ''}${row.failed ? ' is-failed' : ''}`}>
                <span className="story-span-name" style={{ paddingLeft: `${row.depth * 12}px` }}>
                  {children && index > 0 ? (
                    <button
                      type="button"
                      className="story-twisty"
                      aria-expanded={isOpen}
                      aria-label={isOpen ? 'Fold' : 'Unfold'}
                      onClick={() => setToggled((last) => new Map(last).set(row.id, !isOpen))}
                    >
                      {isOpen ? '▾' : '▸'}
                    </button>
                  ) : (
                    <span className="story-twisty" />
                  )}
                  <button type="button" className="story-span-button" onClick={() => select(row, index)} title={row.label}>
                    <span className="story-span-kind">{row.name}</span> {row.label}
                  </button>
                </span>
                <span className="story-span-track">
                  <i className={tone(row)} style={{ left: `${Math.min(99.7, left)}%`, width: `${Math.min(100 - Math.min(99.7, left), width)}%` }} />
                </span>
                <span className="story-fig story-span-ms">{format.duration(row.endMs - row.startMs)}</span>
              </li>
            );
          })}
        </ol>
        {focus !== null && <Detail session={session} step={focus} onSelect={onSelect} />}
      </div>
    </section>
  );
}
