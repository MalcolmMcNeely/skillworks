// PROTOTYPE — throwaway. Variant A's conversation: one fold per prompt, holding what was typed, what the model wrote
// in order, and the tool calls between its words folded away until asked for.

import { useMemo, useState } from 'react';
import type { ModelStep, Session, ToolStep } from '../sessionModel';
import { format, type Exchange } from '../sessionMeasures';
import { DrillOutput, DrillWords } from './DrillWords';

type Block = { kind: 'words'; call: ModelStep } | { kind: 'tools'; id: string; tools: ToolStep[] };

function toggle(set: Set<string>, value: string) {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

function blocksOf(exchange: Exchange): Block[] {
  const blocks: Block[] = [];
  for (const turn of exchange.turns) {
    if (turn.call.said !== null) blocks.push({ kind: 'words', call: turn.call });
    if (turn.tools.length === 0) continue;
    const last = blocks[blocks.length - 1];
    if (last?.kind === 'tools') last.tools.push(...turn.tools);
    else blocks.push({ kind: 'tools', id: turn.tools[0].id, tools: [...turn.tools] });
  }
  return blocks;
}

export function DrillConversation({
  session,
  exchanges,
  zoomed,
  onOpen,
  onZoom,
}: {
  session: Session;
  exchanges: Exchange[];
  zoomed: number | null;
  onOpen: (stepId: string) => void;
  onZoom: (prompt: number) => void;
}) {
  const [folds, setFolds] = useState<Map<number, boolean>>(new Map());
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());
  const [openTools, setOpenTools] = useState<Set<string>>(new Set());

  const stats = useMemo(
    () =>
      session.prompts.map((span) => {
        const steps = session.steps.filter((step) => step.prompt === span.index);
        return {
          calls: steps.filter((step) => step.kind === 'model').length,
          tools: steps.filter((step) => step.kind === 'tool').length,
          failed: steps.filter((step) => (step.kind === 'tool' && !step.ok) || step.kind === 'modelError' || step.kind === 'rejected').length,
          cost: steps.reduce((sum, step) => sum + (step.kind === 'model' ? step.costUsd : 0), 0),
        };
      }),
    [session],
  );

  const isOpen = (index: number) => folds.get(index) ?? (index === zoomed || (zoomed === null && exchanges.length <= 2 && index === 0));

  return (
    <section className="drill-frame drill-convo" aria-labelledby="drill-convo-title">
      <div className="drill-frame-head">
        <h2 id="drill-convo-title">Conversation</h2>
        <span className="drill-sub">What was typed and what the model wrote, prompt by prompt. Tool calls fold between the words.</span>
        <div className="drill-zoom">
          <button type="button" className="drill-key" onClick={() => setFolds(new Map(exchanges.map((each) => [each.span.index, true])))}>
            Open all
          </button>
          <button type="button" className="drill-key" onClick={() => setFolds(new Map(exchanges.map((each) => [each.span.index, false])))}>
            Close all
          </button>
        </div>
      </div>

      {!session.switches.prompts || !session.switches.responses ? (
        <p className="drill-withheld drill-policy">
          <span>This repository keeps the words out of the store. Lengths still arrive.</span>
          <code>
            {!session.switches.prompts && 'OTEL_LOG_USER_PROMPTS=1 '}
            {!session.switches.responses && 'OTEL_LOG_ASSISTANT_RESPONSES=1 '}
            {!session.switches.toolContent && 'OTEL_LOG_TOOL_CONTENT=1'}
          </code>
        </p>
      ) : null}

      <ol className="drill-exchanges">
        {exchanges.map((exchange) => {
          const index = exchange.span.index;
          const open = isOpen(index);
          const stat = stats[index];
          const typed = exchange.prompt.said;
          return (
            <li key={index} className={`drill-exchange${open ? ' is-open' : ''}${index === zoomed ? ' is-zoomed' : ''}`}>
              <button type="button" className="drill-exchange-head" aria-expanded={open} onClick={() => setFolds(new Map(folds).set(index, !open))}>
                <span className="drill-exchange-p">P{index + 1}</span>
                <time>{format.clock(exchange.span.startMs)}</time>
                <span className="drill-exchange-text">
                  {exchange.prompt.command && !typed.text?.startsWith(`/${exchange.prompt.command}`) ? `/${exchange.prompt.command} ` : ''}
                  {typed.text ?? <span className="drill-withheld-inline">Words withheld · {format.int(typed.length)} characters</span>}
                </span>
                <span className="drill-fig drill-faint">
                  {format.short(exchange.span.endMs - exchange.span.startMs)} · {stat.calls} calls · {stat.tools} tools · {format.usd(stat.cost)}
                </span>
                {stat.failed > 0 && <span className="drill-fig drill-bad">◆{stat.failed}</span>}
                <span className="drill-caret" aria-hidden="true">
                  {open ? '▾' : '▸'}
                </span>
              </button>

              {open && (
                <div className="drill-exchange-body">
                  <div className="drill-turn is-you">
                    <span className="drill-who">
                      Typed{exchange.prompt.command ? ` · /${exchange.prompt.command}` : ''} · {format.clock(exchange.prompt.at, true)}
                    </span>
                    <DrillWords said={typed} setting="prompts" />
                  </div>

                  {exchange.skills.length > 0 && (
                    <p className="drill-fired">
                      {exchange.skills.map((skill) => (
                        <button key={skill.id} type="button" className="drill-chip" onClick={() => onOpen(skill.id)}>
                          ⚑ {skill.skill} <span className="drill-faint">{format.trigger(skill.trigger)}</span>
                        </button>
                      ))}
                    </p>
                  )}

                  {blocksOf(exchange).map((block) =>
                    block.kind === 'words' ? (
                      <div key={block.call.id} className={`drill-turn is-claude${block.call === exchange.answer ? ' is-answer' : ''}`}>
                        <span className="drill-who">
                          <button type="button" className="drill-link" onClick={() => onOpen(block.call.id)}>
                            {block.call === exchange.answer ? 'Answer' : 'Model'} · {format.clock(block.call.at, true)} · {format.model(block.call.model)}
                            {block.call.skill ? ` · ${block.call.skill}` : ''}
                          </button>
                        </span>
                        <DrillWords said={block.call.said!} setting="responses" />
                      </div>
                    ) : (
                      <div key={block.id} className="drill-toolrun">
                        <button type="button" className="drill-toolrun-head" aria-expanded={openGroups.has(block.id)} onClick={() => setOpenGroups(toggle(openGroups, block.id))}>
                          {openGroups.has(block.id) ? '▾' : '▸'} {block.tools.length} tool call{block.tools.length === 1 ? '' : 's'}
                          <span className="drill-faint"> · {[...new Set(block.tools.map((tool) => tool.tool))].join(', ')}</span>
                          {block.tools.some((tool) => !tool.ok) && <span className="drill-bad"> · {block.tools.filter((tool) => !tool.ok).length} failed</span>}
                        </button>
                        {openGroups.has(block.id) && (
                          <ol className="drill-tools">
                            {block.tools.map((tool) => (
                              <li key={tool.id} className={tool.ok ? '' : 'is-fail'}>
                                <div className="drill-tool-row">
                                  <button type="button" className="drill-tool-toggle" aria-expanded={openTools.has(tool.id)} onClick={() => setOpenTools(toggle(openTools, tool.id))}>
                                    {openTools.has(tool.id) ? '▾' : '▸'} <b>{tool.tool}</b> <code>{tool.summary}</code>
                                  </button>
                                  <span className="drill-fig drill-faint">{format.duration(tool.ms)}</span>
                                  <button type="button" className="drill-link" onClick={() => onOpen(tool.id)}>
                                    trace
                                  </button>
                                </div>
                                {!tool.ok && <p className="drill-err">{tool.errorType} · {tool.error}</p>}
                                {openTools.has(tool.id) && (
                                  <div className="drill-io">
                                    <span className="drill-micro">Input</span>
                                    <pre className="drill-pre">{tool.input}</pre>
                                    <span className="drill-micro">Output</span>
                                    <DrillOutput output={tool.output} bytes={tool.outputBytes} />
                                  </div>
                                )}
                              </li>
                            ))}
                          </ol>
                        )}
                      </div>
                    ),
                  )}

                  {exchange.subagents.length > 0 && (
                    <p className="drill-fired">
                      {exchange.subagents.map((agent) => (
                        <button key={agent.id} type="button" className="drill-chip" onClick={() => onOpen(agent.id)}>
                          ⑂ {agent.agentType}: {agent.description} <span className="drill-faint">{format.duration(agent.ms)}</span>
                        </button>
                      ))}
                    </p>
                  )}

                  {exchange.answer === null && <p className="drill-fine">No answer yet: this prompt is still running.</p>}

                  <button type="button" className="drill-key drill-zoom-to" onClick={() => onZoom(index)}>
                    Zoom the charts to prompt {index + 1}
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
