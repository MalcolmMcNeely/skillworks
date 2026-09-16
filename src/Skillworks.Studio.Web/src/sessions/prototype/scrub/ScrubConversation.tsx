// PROTOTYPE — throwaway. The Conversation tab: what was typed and what the model wrote, prompt by prompt. It follows the
// brush: prompts in view are marked and scrolled to, and clicking a prompt brushes the timeline to it.

import { memo, useEffect, useRef, useState } from 'react';
import type { Session } from '../sessionModel';
import { format, type Exchange } from '../sessionMeasures';
import { overlaps, settings, windowAround, type Range } from './scrubRange';
import { ScrubToolContent, ScrubWords } from './ScrubWords';

function Turns({ exchange, onStep }: { exchange: Exchange; onStep: (id: string) => void }) {
  const [openTool, setOpenTool] = useState<string | null>(null);

  return (
    <ol className="scrub-turns">
      {exchange.turns.map(({ call, tools }) => (
        <li key={call.id}>
          <div className="scrub-turn-head">
            <button type="button" className="scrub-link" onClick={() => onStep(call.id)}>
              {format.clock(call.at, true)} · model · {format.tokens(call.inputTokens + call.cacheReadTokens + call.cacheCreationTokens)} context · {format.usd(call.costUsd)}
            </button>
            {call.skill !== null && <span className="scrub-chip">{call.skill}</span>}
          </div>
          {call.said !== null && call.stopReason !== 'end_turn' && <ScrubWords said={call.said} setting={settings.responses} clip={600} />}
          {tools.length > 0 && (
            <ul className="scrub-turn-tools">
              {tools.map((tool) => (
                <li key={tool.id} className={tool.ok ? '' : 'is-failed'}>
                  <button type="button" className="scrub-tool-row" aria-expanded={openTool === tool.id} onClick={() => setOpenTool(openTool === tool.id ? null : tool.id)}>
                    <span className="scrub-tool-name">{tool.tool}</span>
                    <span className="scrub-tool-summary">{tool.summary}</span>
                    <span className="scrub-tool-ms">{tool.ok ? format.duration(tool.ms) : 'failed'}</span>
                  </button>
                  {openTool === tool.id && (
                    <div className="scrub-tool-open">
                      <ScrubToolContent tool={tool} />
                      <button type="button" className="scrub-small-button" onClick={() => onStep(tool.id)}>
                        Open in the trace
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ol>
  );
}

export const ScrubConversation = memo(function ScrubConversation({
  session,
  exchanges,
  range,
  onRange,
  onStep,
}: {
  session: Session;
  exchanges: Exchange[];
  range: Range | null;
  onRange: (range: Range) => void;
  onStep: (id: string) => void;
}) {
  const [open, setOpen] = useState<Set<number>>(() => new Set());
  const list = useRef<HTMLOListElement>(null);

  // Scroll only when the brush moves somewhere new, not while the reader scrolls the list on their own.
  const firstInView = exchanges.find((exchange) => overlaps(exchange.span.startMs, exchange.span.endMs, range))?.span.index ?? null;
  useEffect(() => {
    if (range === null || firstInView === null) return;
    list.current?.querySelector(`[data-prompt="${firstInView}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [firstInView, range]);

  const toggle = (index: number) => {
    const next = new Set(open);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setOpen(next);
  };

  return (
    <ol className="scrub-conversation" ref={list}>
      {exchanges.map((exchange) => {
        const inView = range !== null && overlaps(exchange.span.startMs, exchange.span.endMs, range);
        const cost = exchange.turns.reduce((sum, turn) => sum + turn.call.costUsd, 0);
        const toolCount = exchange.turns.reduce((sum, turn) => sum + turn.tools.length, 0);
        const failed = exchange.turns.reduce((sum, turn) => sum + turn.tools.filter((tool) => !tool.ok).length, 0);
        const expanded = open.has(exchange.span.index);

        return (
          <li key={exchange.span.index} data-prompt={exchange.span.index} className={`scrub-exchange${inView ? ' is-in-view' : ''}`}>
            <button type="button" className="scrub-exchange-head" onClick={() => onRange(windowAround(exchange.span.startMs, exchange.span.endMs, session))}>
              <b>Prompt {exchange.span.index + 1}</b>
              <span>{format.clock(exchange.span.startMs)}</span>
              <span>{format.duration(exchange.span.endMs - exchange.span.startMs)}</span>
              <span>{exchange.turns.length} model calls</span>
              <span>{toolCount} tools</span>
              {failed > 0 && <span className="is-failed">{failed} failed</span>}
              <span>{format.usd(cost)}</span>
              {inView && <span className="scrub-in-view">In view</span>}
            </button>

            <div className="scrub-exchange-body">
              <p className="scrub-speaker">
                {session.person}
                {exchange.prompt.command ? ` · /${exchange.prompt.command}` : ''}
              </p>
              <ScrubWords said={exchange.prompt.said} setting={settings.prompts} />

              {exchange.skills.length > 0 && (
                <p className="scrub-chips">
                  {exchange.skills.map((skill) => (
                    <span key={skill.id} className="scrub-chip">
                      {skill.skill} · {format.trigger(skill.trigger)}
                    </span>
                  ))}
                </p>
              )}

              {exchange.turns.length > 0 && (
                <button type="button" className="scrub-small-button" aria-expanded={expanded} onClick={() => toggle(exchange.span.index)}>
                  {expanded ? 'Hide' : 'Show'} the {exchange.turns.length} model calls and {toolCount} tool calls in between
                </button>
              )}
              {expanded && <Turns exchange={exchange} onStep={onStep} />}

              <p className="scrub-speaker is-model">Claude</p>
              {exchange.answer?.said ? (
                <ScrubWords said={exchange.answer.said} setting={settings.responses} />
              ) : (
                <p className="scrub-quiet">{session.running && exchange.span.index === session.prompts.length - 1 ? 'Still working.' : 'No final reply.'}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
});
