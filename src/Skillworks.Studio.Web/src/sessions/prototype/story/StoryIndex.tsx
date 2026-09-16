// PROTOTYPE — throwaway. The way in: a repository, then its sessions by time or by person.

import { useEffect, useMemo } from 'react';
import type { Session } from '../sessionModel';
import { costOf, daysOf, format, peopleIn, repositories, repositoryLabel, sessionName } from '../sessionMeasures';
import type { SessionView } from '../useSessionView';

const initials = (handle: string) =>
  handle
    .split(/[.\-_]/)
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()
    .slice(0, 2);

const faultsOf = (session: Session) =>
  session.steps.filter((step) => (step.kind === 'tool' && !step.ok) || step.kind === 'modelError' || step.kind === 'rejected').length;

interface Group {
  key: string;
  title: string;
  facts: string;
  person: string | null;
  sessions: Session[];
}

export function StoryIndex({ view }: { view: SessionView }) {
  const { sessions, now, place, go } = view;
  const rows = useMemo(() => repositories(sessions), [sessions]);
  const running = sessions.filter((session) => session.running);
  const facts = useMemo(() => new Map(sessions.map((session) => [session.id, { cost: costOf(session), faults: faultsOf(session) }])), [sessions]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const chosen = place.repository;
  const inRepository = chosen === null ? [] : sessions.filter((session) => session.repository === chosen && (place.person === null || session.person === place.person));

  // Lengths run from seconds to a working day, so the bars are on a log scale and the figure beside each one is exact.
  const longest = Math.max(60_000, ...inRepository.map((session) => session.endMs - session.startMs));
  const lengthShare = (ms: number) => Math.max(0.02, Math.log10(Math.max(ms, 1000) / 1000) / Math.log10(longest / 1000));

  const groups: Group[] =
    chosen === null
      ? []
      : place.by === 'person'
        ? peopleIn(sessions, chosen)
            .filter((row) => place.person === null || row.person === place.person)
            .map((row) => ({
              key: row.person,
              title: row.person,
              facts: `${row.sessions.length} session${row.sessions.length === 1 ? '' : 's'} · last ${format.ago(row.lastMs, now)} · ${format.usd(row.costUsd)}`,
              person: row.person,
              sessions: row.sessions.toSorted((a, b) => b.startMs - a.startMs),
            }))
        : daysOf(inRepository, now).map((row) => ({
            key: String(row.dayMs),
            title: row.label,
            facts: `${row.sessions.length} session${row.sessions.length === 1 ? '' : 's'} · ${format.usd(row.sessions.reduce((sum, session) => sum + (facts.get(session.id)?.cost ?? 0), 0))}`,
            person: null,
            sessions: row.sessions,
          }));

  const open = (session: Session) => go({ session: session.id, prompt: null, step: null, activation: null });

  return (
    <div className="story-index">
      <header className="story-index-head">
        <h1>Sessions</h1>
        <span className="story-micro">Prototype · a made-up fortnight · {sessions.length} sessions</span>
      </header>

      {running.length > 0 && (
        <section className="story-live" aria-label="Running now">
          <span className="story-micro">Running now</span>
          {running.map((session) => (
            <button key={session.id} type="button" className="story-live-row" onClick={() => go({ repository: session.repository, session: session.id, prompt: null, step: null, activation: null })}>
              <span className="story-live-dot" aria-hidden="true" />
              <span>{session.person}</span>
              <strong>{sessionName(session)}</strong>
              <span className="story-fig">{repositoryLabel(session.repository)}</span>
              <span className="story-fig">{format.duration(now - session.startMs)} so far</span>
            </button>
          ))}
        </section>
      )}

      <section aria-label="Repositories">
        <p className="story-micro story-step-label">1 · Repository</p>
        <div className="story-repos">
          {rows.map((row) => (
            <button
              key={row.repository || '~none'}
              type="button"
              className="story-repo"
              aria-pressed={chosen === row.repository}
              onClick={() => go({ repository: row.repository, person: null })}
            >
              <span className="story-repo-name">{repositoryLabel(row.repository)}</span>
              <span className="story-repo-figure">{row.sessions}</span>
              <span className="story-micro">sessions</span>
              <span className="story-people">
                {row.people.map((person) => (
                  <span key={person} className="story-initials" title={person}>
                    {initials(person)}
                  </span>
                ))}
              </span>
              <span className="story-repo-foot">
                <span>last {format.ago(row.lastMs, now)}</span>
                <span>{format.usd(row.costUsd)}</span>
              </span>
              {row.running > 0 && <span className="story-badge is-live">{row.running} running</span>}
            </button>
          ))}
        </div>
      </section>

      {chosen === null ? (
        <p className="story-quiet">Choose a repository to see its sessions.</p>
      ) : (
        <section aria-label="Sessions" className="story-list">
          <div className="story-list-head">
            <p className="story-micro story-step-label">2 · Sessions in {repositoryLabel(chosen)}</p>
            <div className="story-keys" role="group" aria-label="Group sessions">
              <button type="button" className="story-key" aria-pressed={place.by === 'recent'} onClick={() => go({ by: 'recent' })}>
                By time
              </button>
              <button type="button" className="story-key" aria-pressed={place.by === 'person'} onClick={() => go({ by: 'person' })}>
                By person
              </button>
            </div>
            {place.person !== null && (
              <button type="button" className="story-chip" onClick={() => go({ person: null })}>
                Only {place.person} ×
              </button>
            )}
          </div>

          <div className="story-table-wrap">
            <table className="story-table">
              <thead>
                <tr>
                  <th scope="col">Started</th>
                  <th scope="col">Person</th>
                  <th scope="col">Session</th>
                  <th scope="col">Length</th>
                  <th scope="col" className="is-number">
                    Prompts
                  </th>
                  <th scope="col" className="is-number">
                    Cost
                  </th>
                  <th scope="col" className="is-number">
                    Faults
                  </th>
                </tr>
              </thead>
              {groups.map((group) => (
                <tbody key={group.key}>
                  <tr className="story-group">
                    <th colSpan={7} scope="rowgroup">
                      {group.person !== null ? (
                        <button type="button" className="story-group-button" onClick={() => go({ person: place.person === group.person ? null : group.person })}>
                          <span className="story-initials">{initials(group.person)}</span>
                          <b>{group.title}</b>
                        </button>
                      ) : (
                        <b>{group.title}</b>
                      )}
                      <span>{group.facts}</span>
                    </th>
                  </tr>
                  {group.sessions.map((session) => {
                    const fact = facts.get(session.id);
                    const length = session.endMs - session.startMs;
                    return (
                      <tr key={session.id} className="story-row" onClick={() => open(session)}>
                        <td className="story-fig">
                          {place.by === 'person' && <span className="story-day">{format.day(session.startMs)} </span>}
                          {format.clock(session.startMs)}
                        </td>
                        <td>{session.person}</td>
                        <td className="story-name">
                          <button
                            type="button"
                            className="story-row-open"
                            onClick={(event) => {
                              event.stopPropagation();
                              open(session);
                            }}
                          >
                            {sessionName(session)}
                          </button>
                          {session.running && <span className="story-badge is-live">running</span>}
                          {session.entry === 'scripted' && <span className="story-badge">claude -p</span>}
                        </td>
                        <td>
                          <span className="story-length">
                            <span className="story-length-track">
                              <i style={{ width: `${lengthShare(length) * 100}%` }} />
                            </span>
                            <span className="story-fig">{format.short(length)}</span>
                          </span>
                        </td>
                        <td className="is-number story-fig">{session.prompts.length}</td>
                        <td className="is-number story-fig">{format.usd(fact?.cost ?? 0)}</td>
                        <td className={`is-number story-fig${(fact?.faults ?? 0) > 0 ? ' story-bad' : ' story-faint'}`}>{(fact?.faults ?? 0) > 0 ? `◆ ${fact?.faults}` : '0'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              ))}
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
