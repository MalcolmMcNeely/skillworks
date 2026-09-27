import { Link } from 'react-router';
import { describeCount, describeMoney } from '../../shared/figures/lib/figures';
import type { Filter } from '../../shared/filters/lib/filters';
import { nowhere, sessionAddress } from '../../shared/session/lib/where';
import {
  describeRunLength,
  describeStarted,
  measureWords,
  noRepository,
  notKnown,
  rowParams,
  sessionHeadings,
  type DrawnSession,
  type Measured,
  type SessionsAnswer,
} from '../lib/sessions';

// Blank and busy, as the rail and the Map already say a figure is on its way that way.
function Cell({ measured, describe }: { measured: Measured; describe: (value: number) => string }) {
  if (measured.state === 'landed') {
    return <td className="session-figure">{describe(measured.value)}</td>;
  }

  if (measured.state === 'arriving') {
    return <td className="session-figure is-arriving" aria-busy={true} />;
  }

  return <td className="session-figure">{measureWords.fellShort}</td>;
}

function Row({ row, filter }: { row: DrawnSession; filter: Filter }) {
  const { session, measures } = row;

  return (
    <tr>
      <td className="session-started">{describeStarted(session.startedUtc)}</td>
      <td>{session.repository ?? noRepository}</td>
      <td>{session.person ?? notKnown}</td>
      <td className="session-name">
        <Link to={sessionAddress(session.id, nowhere, rowParams(session, filter))}>{session.name}</Link>
        {session.running ? <span className="session-running">Running</span> : null}
      </td>
      <td className="session-figure">{describeRunLength(session.lengthMs)}</td>
      <Cell measured={measures.toolCalls} describe={describeCount} />
      <Cell measured={measures.cost} describe={describeMoney} />
      <Cell measured={measures.faults} describe={describeCount} />
    </tr>
  );
}

// The rows draw as soon as they land, and the head above says whether the answer has ended.
export function SessionTable({
  answer,
  failure,
  noRuns,
  filter,
}: {
  answer: SessionsAnswer | null;
  failure: string | null;
  noRuns: string;
  filter: Filter;
}) {
  if (failure !== null) {
    return <p className="session-word">{notKnown}</p>;
  }

  if (answer === null || !answer.landed) {
    return <p className="session-word">Reading the runs…</p>;
  }

  if (answer.rows.length === 0) {
    return <p className="session-word">{noRuns}</p>;
  }

  return (
    <table className="sessions-table">
      <caption className="visually-hidden">Sessions, the newest work first</caption>
      <thead>
        <tr>
          {sessionHeadings.map((heading) => (
            <th key={heading} scope="col">
              {heading}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {answer.rows.map((row) => (
          <Row key={row.session.id} row={row} filter={filter} />
        ))}
      </tbody>
    </table>
  );
}
