// PROTOTYPE — throwaway. Variant A's trace drawer: the prompt's span tree as a waterfall, and the chosen span's details.

import { useEffect, useMemo, useRef, useState } from 'react';
import type { ModelStep, Session, SessionStep } from '../sessionModel';
import { format, startOf, traceFor, type TraceRow } from '../sessionMeasures';
import { DrillOutput, DrillWords } from './DrillWords';

const glyphs: Record<TraceRow['name'], string> = {
  interaction: '◉',
  llm_request: '◆',
  tool: '▣',
  'tool.blocked_on_user': '⏸',
  'tool.execution': '▸',
  hook: '↪',
  subagent: '⑂',
  error: '✕',
};

const ownerOf = (rowId: string) => rowId.split(':')[0];

function attributes(step: SessionStep): [string, string][] {
  const common: [string, string][] = [
    ['span.start', format.clock(startOf(step), true)],
    ['duration', format.duration(step.ms)],
    ['agent_id', step.agent ?? 'main thread'],
  ];
  switch (step.kind) {
    case 'prompt':
      return [['interaction.sequence', String(step.prompt + 1)], ['prompt_length', format.int(step.said.length)], ['command_name', step.command ?? '—'], ...common.slice(0, 1)];
    case 'model':
      return [
        ['query_source', step.querySource],
        ['model', step.model],
        ['effort', step.effort],
        ['stop_reason', step.stopReason],
        ['attempt', String(step.attempt)],
        ['ttft_ms', format.int(step.ttftMs)],
        ['input_tokens', format.int(step.inputTokens)],
        ['cache_read_tokens', format.int(step.cacheReadTokens)],
        ['cache_creation_tokens', format.int(step.cacheCreationTokens)],
        ['output_tokens', format.int(step.outputTokens)],
        ['cost_usd', format.usd(step.costUsd)],
        ['skill.name', step.skill ?? '—'],
        ['request_id', step.requestId],
        ...common,
      ];
    case 'tool':
      return [
        ['tool_name', step.tool],
        ['success', String(step.ok)],
        ...(step.ok ? [] : ([['error_type', step.errorType ?? '—']] as [string, string][])),
        ['blocked_on_user', format.duration(step.waitedMs)],
        ['decision_source', step.allowedBy],
        ['tool_input_size_bytes', format.int(step.inputBytes)],
        ['tool_result_size_bytes', format.int(step.outputBytes)],
        ['tool_use_id', step.toolUseId],
        ...common,
      ];
    case 'rejected':
      return [['tool_name', step.tool], ['decision', 'reject'], ['source', step.source], ...common];
    case 'hook':
      return [['hook_name', step.hook], ['num_hooks', String(step.hooks)], ['num_blocking', String(step.blocking)], ['num_errors', String(step.errors)], ...common];
    case 'subagent':
      return [
        ['agent_type', step.agentType],
        ['agent_id', step.agentId],
        ['final_model', step.model],
        ['total_tokens', format.int(step.tokens)],
        ['total_tool_uses', String(step.toolUses)],
        ['is_async', String(step.async)],
        ...common.slice(0, 2),
      ];
    case 'modelError':
      return [['status_code', String(step.status)], ['model', step.model], ['attempt', String(step.attempt)], ...common];
    case 'skill':
      return [['skill.name', step.skill], ['invocation_trigger', step.trigger], ...common];
  }
}

function Detail({ session, step, onSelect }: { session: Session; step: SessionStep; onSelect: (id: string) => void }) {
  const toolsOf = (call: ModelStep) => session.steps.filter((each) => each.kind === 'tool' && call.toolUseIds.includes(each.toolUseId));
  const report = step.kind === 'subagent' ? session.steps.find((each): each is ModelStep => each.kind === 'model' && each.parent === step.id && each.stopReason === 'end_turn') : undefined;

  return (
    <div className="drill-detail">
      {step.kind === 'prompt' && (
        <>
          <h4 className="drill-micro">What was typed</h4>
          <DrillWords said={step.said} setting="prompts" />
        </>
      )}
      {step.kind === 'model' && (
        <>
          <h4 className="drill-micro">What the model wrote</h4>
          {step.said === null ? <p className="drill-fine">No words on this call. It only asked for tools. Thinking is never sent.</p> : <DrillWords said={step.said} setting="responses" />}
          {step.toolUseIds.length > 0 && (
            <>
              <h4 className="drill-micro">It asked for</h4>
              <ul className="drill-asked">
                {toolsOf(step).map((tool) => (
                  <li key={tool.id}>
                    <button type="button" className="drill-link" onClick={() => onSelect(tool.id)}>
                      {tool.kind === 'tool' ? `${tool.tool} · ${tool.summary}` : tool.id}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
      {step.kind === 'tool' && (
        <>
          {!step.ok && <p className="drill-err">{step.errorType} · {step.error}</p>}
          <h4 className="drill-micro">Input · sent to the tool</h4>
          <pre className="drill-pre">{step.input}</pre>
          <h4 className="drill-micro">Output · what came back</h4>
          <DrillOutput output={step.output} bytes={step.outputBytes} />
        </>
      )}
      {step.kind === 'rejected' && <pre className="drill-pre">{step.summary}</pre>}
      {step.kind === 'modelError' && <p className="drill-err">{step.message}</p>}
      {step.kind === 'subagent' && (
        <>
          <h4 className="drill-micro">Task</h4>
          <p className="drill-fine">{step.description}</p>
          <h4 className="drill-micro">What it reported back</h4>
          {report?.said ? <DrillWords said={report.said} setting="responses" /> : <p className="drill-fine">No report found.</p>}
        </>
      )}
      <h4 className="drill-micro">Attributes</h4>
      <dl className="drill-attrs">
        {attributes(step).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function DrillTrace({ session, stepId, onSelect, onClose }: { session: Session; stepId: string; onSelect: (id: string) => void; onClose: () => void }) {
  const trace = useMemo(() => traceFor(session, stepId), [session, stepId]);
  const [hooks, setHooks] = useState(true);
  const [phases, setPhases] = useState(false);
  const [scale, setScale] = useState<'near' | 'prompt'>('near');
  const rows = useMemo(
    () => (trace === null ? [] : trace.rows.filter((row) => (hooks || row.name !== 'hook') && (phases || row.name !== 'tool.execution'))),
    [trace, hooks, phases],
  );
  const selectable = rows.filter((row) => row.step !== null);
  const step = session.steps.find((each) => each.id === stepId) ?? null;

  const list = useRef<HTMLOListElement>(null);

  // Only when the choice changes, so a reader scrolling the waterfall is not pulled back on every render.
  useEffect(() => {
    list.current?.querySelector(`[data-span="${CSS.escape(stepId)}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [stepId]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
      const at = selectable.findIndex((row) => row.id === stepId);
      const next = selectable[Math.max(0, Math.min(selectable.length - 1, at + (event.key === 'ArrowDown' ? 1 : -1)))];
      if (next) {
        event.preventDefault();
        onSelect(next.id);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectable, stepId, onSelect, onClose]);

  if (trace === null || step === null) {
    return (
      <aside className="drill-drawer" aria-label="Trace">
        <div className="drill-drawer-head">
          <h2>Trace</h2>
          <button type="button" className="drill-key" onClick={onClose} aria-label="Close the trace">
            ×
          </button>
        </div>
        <p className="drill-empty">This step belongs to no prompt, so it has no trace.</p>
      </aside>
    );
  }

  const span = Math.max(1, trace.endMs - trace.startMs);
  const selectedRow = rows.find((row) => row.id === stepId) ?? null;
  const selectedName = selectedRow?.name ?? 'interaction';

  // A long prompt makes every step a sliver, so by default the bars are scaled to a window around the chosen step.
  const pad = selectedRow === null ? 0 : Math.max(20_000, (selectedRow.endMs - selectedRow.startMs) * 1.5);
  const near = scale === 'near' && selectedRow !== null && selectedRow.name !== 'interaction';
  const windowStart = near ? Math.max(trace.startMs, selectedRow.startMs - pad) : trace.startMs;
  const windowEnd = near ? Math.min(trace.endMs, selectedRow.endMs + pad) : trace.endMs;
  const windowMs = Math.max(1, windowEnd - windowStart);

  return (
    <aside className="drill-drawer" aria-label="Trace">
      <div className="drill-drawer-head">
        <div>
          <p className="drill-micro">Trace · prompt {trace.prompt.index + 1} of {session.prompts.length}</p>
          <h2>
            {trace.rows.length} spans in {format.duration(span)}
          </h2>
        </div>
        <div className="drill-zoom">
          <button type="button" className="drill-key" aria-pressed={hooks} onClick={() => setHooks(!hooks)}>
            Hooks
          </button>
          <button type="button" className="drill-key" aria-pressed={phases} onClick={() => setPhases(!phases)}>
            Tool runs
          </button>
          <button type="button" className="drill-key" aria-pressed={scale === 'near'} onClick={() => setScale(scale === 'near' ? 'prompt' : 'near')} title="Scale the bars to the chosen step or to the whole prompt">
            {scale === 'near' ? 'Near this step' : 'Whole prompt'}
          </button>
          <button type="button" className="drill-key" onClick={onClose} aria-label="Close the trace">
            ×
          </button>
        </div>
      </div>

      <div className="drill-waterfall-scale" aria-hidden="true">
        <span>{format.clock(windowStart, true)}</span>
        <span>+{format.short(windowMs / 2)}</span>
        <span>+{format.short(windowMs)}</span>
      </div>

      <ol ref={list} className="drill-waterfall">
        {rows.map((row) => {
          const owner = row.step === null ? ownerOf(row.id) : row.id;
          const on = row.id === stepId;
          const from = Math.max(0, Math.min(100, ((row.startMs - windowStart) / windowMs) * 100));
          const to = Math.max(0, Math.min(100, ((row.endMs - windowStart) / windowMs) * 100));
          const offset = Math.min(99.6, from);
          const width = Math.max(0.4, to - from);
          const outside = row.endMs < windowStart || row.startMs > windowEnd;
          return (
            <li key={row.id} data-span={row.id} className={`drill-span drill-s-${row.name.replace('.', '-')}${on ? ' is-on' : ''}${row.failed ? ' is-fail' : ''}${owner === stepId && !on ? ' is-part' : ''}`}>
              <button type="button" onClick={() => onSelect(owner)}>
                <span className="drill-span-name" style={{ paddingLeft: `${row.depth * 12}px` }}>
                  <span className="drill-span-glyph" aria-hidden="true">
                    {glyphs[row.name]}
                  </span>
                  {row.label}
                </span>
                <span className="drill-span-track">
                  <span className={`drill-span-bar${outside ? ' is-outside' : ''}`} style={{ left: `${offset}%`, width: `${Math.min(100 - offset, width)}%` }} />
                </span>
                <span className="drill-fig drill-faint">{format.duration(row.endMs - row.startMs)}</span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="drill-drawer-detail">
        <p className="drill-micro">
          {selectedName} · {format.clock(startOf(step), true)}
        </p>
        <h3 className="drill-detail-title">{rows.find((row) => row.id === stepId)?.label ?? step.id}</h3>
        <Detail session={session} step={step} onSelect={onSelect} />
      </div>
    </aside>
  );
}
