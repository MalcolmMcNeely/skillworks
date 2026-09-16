import {
  describeLength,
  describeStarted,
  noRepository,
  notKnown,
  type Session,
  type SessionsAnswer,
} from '../lib/sessions';

function Row({ session }: { session: Session }) {
  return (
    <tr>
      <td className="session-started">{describeStarted(session.startedUtc)}</td>
      <td>{session.repository ?? noRepository}</td>
      <td>{session.person ?? notKnown}</td>
      <td className="session-name">
        <span>{session.name}</span>
        {session.running ? <span className="session-running">Running</span> : null}
      </td>
      <td className="session-length">{describeLength(session.lengthMs)}</td>
    </tr>
  );
}

// The rows draw as soon as they land, and the head above says whether the answer has ended.
export function SessionTable({ answer, failure }: { answer: SessionsAnswer | null; failure: string | null }) {
  if (failure !== null) {
    return <p className="session-word">{notKnown}</p>;
  }

  if (answer === null || !answer.landed) {
    return <p className="session-word">Reading the runs…</p>;
  }

  if (answer.sessions.length === 0) {
    return <p className="session-word">No runs in this period.</p>;
  }

  return (
    <table className="sessions-table">
      <caption className="visually-hidden">Sessions, newest first</caption>
      <thead>
        <tr>
          <th scope="col">Started</th>
          <th scope="col">Repository</th>
          <th scope="col">Person</th>
          <th scope="col">Session</th>
          <th scope="col">Length</th>
        </tr>
      </thead>
      <tbody>
        {answer.sessions.map((session) => (
          <Row key={session.id} session={session} />
        ))}
      </tbody>
    </table>
  );
}
