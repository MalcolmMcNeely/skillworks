// PROTOTYPE — throwaway. Variant A's way in: three columns, repository then time or person then session. Once a
// session is open they fold to one line of crumbs, and any crumb opens them again.

import { useMemo, useState } from 'react';
import type { Session } from '../sessionModel';
import { costOf, daysOf, format, peopleIn, repositories, repositoryLabel, sessionName } from '../sessionMeasures';
import type { SessionView } from '../useSessionView';

const dayMs = 24 * 60 * 60 * 1000;

const glances = new Map<string, { cost: number; faults: number }>();

// The lists read every session, so each one is counted once per page load.
function glance(session: Session) {
  let found = glances.get(session.id);
  if (found === undefined) {
    found = {
      cost: costOf(session),
      faults: session.steps.filter((step) => (step.kind === 'tool' && !step.ok) || step.kind === 'modelError' || step.kind === 'rejected').length,
    };
    glances.set(session.id, found);
  }
  return found;
}

export function DrillColumns({ view, open, onOpen, onFold }: { view: SessionView; open: boolean; onOpen: () => void; onFold: () => void }) {
  const { sessions, place, go, now, session } = view;
  const repository = place.repository ?? session?.repository ?? null;
  const [picked, setPicked] = useState<{ repository: string; dayMs: number } | null>(null);

  const repos = useMemo(() => repositories(sessions), [sessions]);
  const inRepository = useMemo(() => (repository === null ? [] : sessions.filter((each) => each.repository === repository)), [sessions, repository]);
  const days = useMemo(() => daysOf(inRepository, now), [inRepository, now]);
  const people = useMemo(() => (repository === null ? [] : peopleIn(sessions, repository)), [sessions, repository]);

  const sessionDay = session !== null && session.repository === repository ? Math.floor(session.startMs / dayMs) * dayMs : null;
  const day = (picked !== null && picked.repository === repository ? picked.dayMs : null) ?? sessionDay ?? days[0]?.dayMs ?? null;
  const person = place.person ?? (session !== null && session.repository === repository ? session.person : null) ?? people[0]?.person ?? null;
  const byTime = place.by === 'recent';
  const listed = byTime
    ? (days.find((each) => each.dayMs === day)?.sessions ?? [])
    : (people.find((each) => each.person === person)?.sessions.toSorted((a, b) => b.startMs - a.startMs) ?? []);

  const running = sessions.find((each) => each.running) ?? null;

  const choose = (chosen: Session) => {
    go({ repository: chosen.repository, person: byTime ? place.person : chosen.person, session: chosen.id, prompt: null, step: null, activation: null });
    onFold();
  };

  if (!open && session !== null) {
    const dayLabel = daysOf([session], now)[0].label;
    return (
      <nav className="drill-crumbs" aria-label="Where you are">
        <button type="button" onClick={onOpen}>
          Sessions
        </button>
        <span aria-hidden="true">▸</span>
        <button type="button" onClick={onOpen}>
          {repositoryLabel(session.repository)}
        </button>
        <span aria-hidden="true">▸</span>
        <button type="button" onClick={onOpen}>
          {byTime ? 'By time' : 'By person'}
        </button>
        <span aria-hidden="true">▸</span>
        <button type="button" onClick={onOpen}>
          {byTime ? dayLabel : session.person}
        </button>
        <span aria-hidden="true">▸</span>
        <span className="drill-crumb-here">{sessionName(session)}</span>
        <span className="drill-crumb-hint">Click a crumb to choose another session</span>
      </nav>
    );
  }

  return (
    <nav className="drill-columns" aria-label="Choose a session">
      <div className="drill-col">
        <h2 className="drill-col-head">Repositories</h2>
        <ul className="drill-col-list">
          {repos.map((row) => (
            <li key={row.repository}>
              <button
                type="button"
                className="drill-row"
                aria-pressed={row.repository === repository}
                onClick={() => go({ repository: row.repository, person: null, session: null, prompt: null, step: null, activation: null })}
              >
                <span className="drill-row-main">
                  {row.running > 0 && <i className="drill-live-dot" aria-label="running now" />}
                  {repositoryLabel(row.repository)}
                </span>
                <span className="drill-row-meta">
                  {row.sessions} session{row.sessions === 1 ? '' : 's'} · {row.people.length} {row.people.length === 1 ? 'person' : 'people'}
                </span>
                <span className="drill-row-side">
                  <span>{format.ago(row.lastMs, now)}</span>
                  <span>{format.usd(row.costUsd)}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="drill-col">
        <div className="drill-col-head drill-col-toggle" role="group" aria-label="Group sessions">
          <button type="button" className="drill-key" aria-pressed={byTime} disabled={repository === null} onClick={() => go({ by: 'recent' })}>
            By time
          </button>
          <button type="button" className="drill-key" aria-pressed={!byTime} disabled={repository === null} onClick={() => go({ by: 'person' })}>
            By person
          </button>
        </div>
        {repository === null ? (
          <p className="drill-col-empty">Choose a repository.</p>
        ) : (
          <ul className="drill-col-list">
            {byTime
              ? days.map((row) => (
                  <li key={row.dayMs}>
                    <button type="button" className="drill-row" aria-pressed={row.dayMs === day} onClick={() => setPicked({ repository, dayMs: row.dayMs })}>
                      <span className="drill-row-main">
                        {row.sessions.some((each) => each.running) && <i className="drill-live-dot" aria-label="running now" />}
                        {row.label}
                      </span>
                      <span className="drill-row-meta">{row.sessions.length} session{row.sessions.length === 1 ? '' : 's'}</span>
                      <span className="drill-row-side">
                        <span>{format.usd(row.sessions.reduce((sum, each) => sum + glance(each).cost, 0))}</span>
                      </span>
                    </button>
                  </li>
                ))
              : people.map((row) => (
                  <li key={row.person}>
                    <button type="button" className="drill-row" aria-pressed={row.person === person} onClick={() => go({ person: row.person })}>
                      <span className="drill-row-main">
                        {row.sessions.some((each) => each.running) && <i className="drill-live-dot" aria-label="running now" />}
                        {row.person}
                      </span>
                      <span className="drill-row-meta">{row.sessions.length} session{row.sessions.length === 1 ? '' : 's'}</span>
                      <span className="drill-row-side">
                        <span>{format.ago(row.lastMs, now)}</span>
                        <span>{format.usd(row.costUsd)}</span>
                      </span>
                    </button>
                  </li>
                ))}
          </ul>
        )}
      </div>

      <div className="drill-col drill-col-wide">
        <h2 className="drill-col-head">
          Sessions
          {repository !== null && <span className="drill-faint"> · {byTime ? (days.find((each) => each.dayMs === day)?.label ?? '') : person} · most recent first</span>}
          {session !== null && (
            <button type="button" className="drill-key drill-fold" onClick={onFold}>
              Fold ▴
            </button>
          )}
        </h2>
        {repository === null ? (
          running === null ? (
            <p className="drill-col-empty">Choose a repository.</p>
          ) : (
            <div className="drill-col-empty">
              <p>Choose a repository, or open the session running now:</p>
              <button type="button" className="drill-row" onClick={() => choose(running)}>
                <span className="drill-row-main">
                  <i className="drill-live-dot" aria-label="running now" />
                  {sessionName(running)}
                </span>
                <span className="drill-row-meta">
                  {running.person} · {repositoryLabel(running.repository)} · {format.duration(running.endMs - running.startMs)} so far
                </span>
              </button>
            </div>
          )
        ) : (
          <ul className="drill-col-list">
            {listed.map((each) => {
              const seen = glance(each);
              return (
                <li key={each.id}>
                  <button type="button" className={`drill-row drill-session-row${byTime ? '' : ' is-dated'}`} aria-pressed={each.id === session?.id} onClick={() => choose(each)}>
                    <span className="drill-row-when">{byTime ? format.clock(each.startMs) : `${format.day(each.startMs)} ${format.clock(each.startMs)}`}</span>
                    <span className="drill-row-main">
                      {each.running && <i className="drill-live-dot" aria-label="running now" />}
                      {sessionName(each)}
                    </span>
                    <span className="drill-row-meta">
                      {byTime ? `${each.person} · ` : ''}
                      {format.duration(each.endMs - each.startMs)} · {each.prompts.length} prompt{each.prompts.length === 1 ? '' : 's'}
                      {each.entry === 'scripted' ? ' · claude -p' : ''}
                    </span>
                    <span className="drill-row-side">
                      <span>{format.usd(seen.cost)}</span>
                      {seen.faults > 0 ? <span className="drill-bad">◆ {seen.faults}</span> : <span className="drill-faint">no faults</span>}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </nav>
  );
}
