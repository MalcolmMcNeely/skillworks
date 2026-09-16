// PROTOTYPE — throwaway. The Scrub rail: repository, then recent or by person, then the session. It stays beside the
// instrument, so moving to the next session is one click and never a trip back to a list page.

import { useMemo } from 'react';
import type { Session } from '../sessionModel';
import { costOf, daysOf, format, peopleIn, repositories, repositoryLabel, sessionName } from '../sessionMeasures';
import type { SessionView } from '../useSessionView';
import { lengthShare } from './scrubRange';

const faulted = (session: Session) => session.steps.some((step) => (step.kind === 'tool' && !step.ok) || step.kind === 'modelError');

function SessionRow({ session, view, showPerson }: { session: Session; view: SessionView; showPerson: boolean }) {
  const chosen = view.place.session === session.id;
  const length = session.endMs - session.startMs;

  return (
    <li>
      <button
        type="button"
        className={`scrub-session${chosen ? ' is-chosen' : ''}`}
        aria-pressed={chosen}
        onClick={() => view.go({ repository: session.repository, session: session.id, prompt: null, step: null, activation: null })}
      >
        <span className="scrub-session-name">
          {session.running && <i className="scrub-pulse" aria-label="Running" />}
          {faulted(session) && <i className="scrub-fault-dot" aria-label="Has faults" />}
          <span>{sessionName(session)}</span>
        </span>
        <span className="scrub-session-meta">
          {format.clock(session.startMs)}
          {showPerson ? ` · ${session.person}` : ''} · {format.short(length)} · {format.usd(costOf(session))}
        </span>
        <span className="scrub-length" aria-hidden="true">
          <i style={{ width: `${lengthShare(length) * 100}%` }} />
        </span>
      </button>
    </li>
  );
}

export function ScrubRail({ view, open, onToggle }: { view: SessionView; open: boolean; onToggle: () => void }) {
  const { sessions, place, session, now, go } = view;
  const repository = place.repository ?? session?.repository ?? null;
  const rows = useMemo(() => repositories(sessions), [sessions]);
  const inRepository = useMemo(() => (repository === null ? [] : sessions.filter((each) => each.repository === repository)), [sessions, repository]);

  if (!open) {
    return (
      <aside className="scrub-rail is-shut" aria-label="Sessions">
        <button type="button" className="scrub-rail-toggle" onClick={onToggle} aria-label="Open the session rail">
          »
        </button>
        <span className="scrub-rail-shut-label">{repository === null ? 'Sessions' : repositoryLabel(repository)}</span>
      </aside>
    );
  }

  return (
    <aside className="scrub-rail" aria-label="Sessions">
      <div className="scrub-brand">
        <h2>Sessions</h2>
        <span className="scrub-micro">{sessions.length} in 14 days</span>
        <button type="button" className="scrub-rail-toggle" onClick={onToggle} aria-label="Close the session rail">
          «
        </button>
      </div>

      <section className="scrub-block" aria-label="Repository">
        <p className="scrub-micro">Repository</p>
        <ul className="scrub-repos">
          {rows.map((row) => {
            const chosen = row.repository === repository;
            return (
              <li key={row.repository}>
                <button
                  type="button"
                  className={`scrub-repo${chosen ? ' is-chosen' : ''}`}
                  aria-pressed={chosen}
                  onClick={() => go({ repository: row.repository, person: null, session: null, prompt: null, step: null, activation: null })}
                >
                  <span className="scrub-repo-name">
                    {row.running > 0 && <i className="scrub-pulse" aria-label="Running" />}
                    {repositoryLabel(row.repository)}
                  </span>
                  <span className="scrub-repo-meta">
                    {row.sessions} · {row.people.length} {row.people.length === 1 ? 'person' : 'people'} · {format.ago(row.lastMs, now)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      {repository !== null && (
        <section className="scrub-block scrub-tree" aria-label="Sessions in the repository">
          <div className="scrub-keys" role="group" aria-label="Group sessions">
            <button type="button" className="scrub-key" aria-pressed={place.by === 'recent'} onClick={() => go({ by: 'recent' })}>
              Recent
            </button>
            <button type="button" className="scrub-key" aria-pressed={place.by === 'person'} onClick={() => go({ by: 'person' })}>
              People
            </button>
          </div>

          <div className="scrub-tree-scroll">
            {place.by === 'recent'
              ? daysOf(inRepository, now).map((dayRow) => (
                  <div key={dayRow.dayMs} className="scrub-group">
                    <p className="scrub-group-head">
                      <span>{dayRow.label}</span>
                      <span>{dayRow.sessions.length}</span>
                    </p>
                    <ul>
                      {dayRow.sessions.map((each) => (
                        <SessionRow key={each.id} session={each} view={view} showPerson />
                      ))}
                    </ul>
                  </div>
                ))
              : peopleIn(sessions, repository).map((personRow) => {
                  const openPerson = place.person === personRow.person || (place.person === null && session?.person === personRow.person);
                  return (
                    <div key={personRow.person} className="scrub-group">
                      <button
                        type="button"
                        className={`scrub-person${openPerson ? ' is-open' : ''}`}
                        aria-expanded={openPerson}
                        onClick={() => go({ person: openPerson ? null : personRow.person })}
                      >
                        <span>{openPerson ? '▾' : '▸'} {personRow.person}</span>
                        <span>
                          {personRow.sessions.length} · {format.ago(personRow.lastMs, now)}
                        </span>
                      </button>
                      {openPerson && (
                        <ul>
                          {personRow.sessions.map((each) => (
                            <SessionRow key={each.id} session={each} view={view} showPerson={false} />
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
          </div>
        </section>
      )}
    </aside>
  );
}

export function ScrubPicker({ view }: { view: SessionView }) {
  const { sessions, place, now } = view;
  const shown = (place.repository === null ? sessions : sessions.filter((each) => each.repository === place.repository)).slice(0, 12);

  return (
    <div className="scrub-main scrub-empty">
      <div className="scrub-empty-box">
        <p className="scrub-empty-word">{place.repository === null ? 'Pick a repository' : 'Pick a session'}</p>
        <p className="scrub-empty-note">
          {place.repository === null
            ? 'The rail lists every repository a session ran in. The newest sessions from all of them are below.'
            : `Newest first in ${repositoryLabel(place.repository)}. Switch the rail to People to go by person.`}
        </p>
        <ul className="scrub-empty-list">
          {shown.map((each) => (
            <li key={each.id}>
              <button type="button" className="scrub-empty-row" onClick={() => view.go({ repository: each.repository, session: each.id, prompt: null, step: null, activation: null })}>
                <span className="scrub-session-name">
                  {each.running && <i className="scrub-pulse" aria-label="Running" />}
                  {faulted(each) && <i className="scrub-fault-dot" aria-label="Has faults" />}
                  <span>{sessionName(each)}</span>
                </span>
                <span className="scrub-session-meta">
                  {repositoryLabel(each.repository)} · {each.person} · {format.ago(each.endMs, now)} · {format.short(each.endMs - each.startMs)} · {format.usd(costOf(each))}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
