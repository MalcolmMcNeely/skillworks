// PROTOTYPE — throwaway. Variant A, Drill: columns to find a session, a dashboard that scrolls down through it, and a
// trace drawer that opens beside the dashboard so the chart that was clicked stays in view.

import { useCallback, useMemo, useState } from 'react';
import { format, repositoryLabel, sessionName, summarize, timeSplit } from '../sessionMeasures';
import type { SessionView } from '../useSessionView';
import { DrillColumns } from './DrillColumns';
import { DrillContext } from './DrillContext';
import { DrillConversation } from './DrillConversation';
import { DrillSkills } from './DrillSkills';
import { DrillTime } from './DrillTime';
import { DrillTimeline } from './DrillTimeline';
import { DrillTrace } from './DrillTrace';
import { stepsOfFinding, useDrillSession } from './useDrillSession';
import './DrillVariant.css';

export function DrillVariant({ view }: { view: SessionView }) {
  const { session, place, go } = view;
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [findingKey, setFindingKey] = useState<string | null>(null);
  const measures = useDrillSession(session);

  const zoomed = session !== null && place.prompt !== null && session.prompts[place.prompt] !== undefined ? place.prompt : null;
  const range = useMemo<[number, number] | null>(() => {
    if (session === null || zoomed === null) return null;
    const span = session.prompts[zoomed];
    return [span.startMs, span.endMs];
  }, [session, zoomed]);

  const scoped = useMemo(() => (session === null || range === null ? null : { summary: summarize(session, range), split: timeSplit(session, range) }), [session, range]);

  const finding = measures?.findings.find((each) => each.key === findingKey) ?? null;
  const lit = useMemo(
    () => (session === null || measures === null || finding === null ? null : stepsOfFinding(finding, session.steps, measures.context)),
    [session, measures, finding],
  );

  const activationCount = measures?.activations.length ?? 0;
  const activation = activationCount === 0 ? null : Math.max(0, Math.min(activationCount - 1, place.activation ?? 0));

  const open = useCallback((stepId: string) => go({ step: stepId }), [go]);
  const close = useCallback(() => go({ step: null }), [go]);
  const setActivation = useCallback((index: number) => go({ activation: index }), [go]);
  const zoom = (prompt: number | null) => go({ prompt });

  const drawer = session !== null && place.step !== null;

  return (
    <div className={`drill${drawer ? ' has-drawer' : ''}`}>
      <div className="drill-board">
        <header className="drill-top">
          <span className="drill-brand">Skillworks · Sessions</span>
          <DrillColumns view={view} open={columnsOpen || session === null} onOpen={() => setColumnsOpen(true)} onFold={() => setColumnsOpen(false)} />
        </header>

        {session === null || measures === null ? (
          <p className="drill-empty drill-pick">Pick a repository, then a day or a person, then a session.</p>
        ) : (
          <>
            <header className="drill-head">
              <div>
                <p className="drill-micro">
                  {repositoryLabel(session.repository)} · {session.person} · {session.entry === 'scripted' ? 'claude -p' : 'interactive'} · Claude Code {session.version}
                </p>
                <h1>
                  {session.running && (
                    <span className="drill-running">
                      <i className="drill-live-dot" /> Running
                    </span>
                  )}
                  {sessionName(session)}
                </h1>
                <p className="drill-fine">
                  Started {format.day(session.startMs)} {format.clock(session.startMs)} · {session.running ? `last step ${format.ago(session.endMs, view.now)}` : `ended ${format.clock(session.endMs)}`} ·{' '}
                  <code>{session.id.slice(0, 8)}</code>
                </p>
              </div>
            </header>

            <dl className="drill-tiles">
              <div className="drill-tile is-hero">
                <dt>Cost</dt>
                <dd>{format.usd(measures.summary.costUsd)}</dd>
              </div>
              <div className="drill-tile">
                <dt>Length</dt>
                <dd>{format.duration(measures.summary.wallMs)}</dd>
              </div>
              <div className="drill-tile">
                <dt>Busy</dt>
                <dd>{format.duration(measures.summary.busyMs)}</dd>
              </div>
              <div className="drill-tile">
                <dt>Prompts</dt>
                <dd>{measures.summary.prompts}</dd>
              </div>
              <div className="drill-tile">
                <dt>Model calls</dt>
                <dd>{measures.summary.mainCalls + measures.summary.otherCalls}</dd>
                <dd className="drill-tile-sub">
                  {measures.summary.mainCalls} main · {measures.summary.otherCalls} other
                </dd>
              </div>
              <div className="drill-tile">
                <dt>Tool calls</dt>
                <dd>{measures.summary.toolCalls}</dd>
              </div>
              <div className={`drill-tile${measures.summary.failedTools + measures.summary.apiErrors > 0 ? ' is-bad' : ''}`}>
                <dt>Failed</dt>
                <dd>{measures.summary.failedTools + measures.summary.apiErrors}</dd>
                <dd className="drill-tile-sub">
                  {measures.summary.failedTools} tools · {measures.summary.apiErrors} API
                </dd>
              </div>
              <div className="drill-tile">
                <dt>Subagents</dt>
                <dd>{measures.summary.subagents}</dd>
              </div>
            </dl>

            <div className="drill-findings" role="group" aria-label="Findings">
              <span className="drill-micro">Findings</span>
              {measures.findings.length === 0 && <span className="drill-fine">Nothing stands out.</span>}
              {measures.findings.map((each) => (
                <button
                  key={each.key}
                  type="button"
                  className={`drill-finding is-${each.tone}`}
                  aria-pressed={each.key === findingKey}
                  title={each.detail}
                  onClick={() => setFindingKey(each.key === findingKey ? null : each.key)}
                >
                  <i aria-hidden="true" />
                  {each.title}
                  <span className="drill-finding-detail">{each.detail}</span>
                </button>
              ))}
              {finding !== null && (
                <span className="drill-fine">
                  Lit on the timeline. {lit?.size ?? 0} step{lit?.size === 1 ? '' : 's'}.
                </span>
              )}
            </div>

            <DrillTimeline
              session={session}
              zoomed={zoomed}
              activations={measures.activations}
              activation={activation}
              lit={lit}
              selected={place.step}
              onOpen={open}
              onZoom={zoom}
              onActivation={setActivation}
            />

            <div className="drill-two">
              <DrillTime
                parts={(scoped?.split ?? measures.split).parts}
                kinds={(scoped?.split ?? measures.split).kinds}
                wallMs={range === null ? session.endMs - session.startMs : range[1] - range[0]}
                scope={zoomed === null ? 'the whole session' : `prompt ${zoomed + 1}`}
              />
              <DrillContext
                session={session}
                points={zoomed === null ? measures.context : measures.context.filter((point) => point.step.prompt === zoomed)}
                activations={measures.activations}
                activation={activation}
                limit={session.contextLimit}
                onOpen={open}
              />
            </div>

            <DrillSkills session={session} activations={measures.activations} index={activation ?? 0} onIndex={setActivation} onOpen={open} />

            <DrillConversation session={session} exchanges={measures.exchanges} zoomed={zoomed} onOpen={open} onZoom={zoom} />
          </>
        )}
      </div>

      {drawer && session !== null && place.step !== null && <DrillTrace session={session} stepId={place.step} onSelect={open} onClose={close} />}
    </div>
  );
}
