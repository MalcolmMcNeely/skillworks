import { describeCount, describeMoney } from '../../figures/lib/figures';
import {
  describeLength,
  describeStarted,
  noRepository,
  notKnown,
  sessionColumns,
  sortGlyphs,
  type Session,
  type SessionColumn,
  type SessionSort,
  type SessionsAnswer,
  type SortedBy,
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
      <td className="session-figure">{describeLength(session.lengthMs)}</td>
      <td className="session-figure">{describeCount(session.toolCalls)}</td>
      <td className="session-figure">{describeMoney(session.cost)}</td>
      <td className="session-figure">{describeCount(session.faults)}</td>
    </tr>
  );
}

// The mark comes from the answer, never from what was asked, so a heading never claims an order that did not happen.
function Heading({
  column,
  sortedBy,
  onSort,
}: {
  column: SessionColumn;
  sortedBy: SortedBy;
  onSort: (sort: SessionSort) => void;
}) {
  const sorted = sortedBy.sort === column.sort;
  const glyph = sortedBy.descending ? sortGlyphs.descending : sortGlyphs.ascending;

  return (
    <th scope="col" aria-sort={sorted ? (sortedBy.descending ? 'descending' : 'ascending') : 'none'}>
      <button type="button" className="session-sort" onClick={() => onSort(column.sort)}>
        {column.heading}
        <span className="session-sort-mark" aria-hidden="true">
          {sorted ? glyph : ''}
        </span>
      </button>
    </th>
  );
}

// The rows draw as soon as they land, and the head above says whether the answer has ended.
export function SessionTable({
  answer,
  failure,
  onSort,
}: {
  answer: SessionsAnswer | null;
  failure: string | null;
  onSort: (sort: SessionSort) => void;
}) {
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
      <caption className="visually-hidden">Sessions, sorted on any column</caption>
      <thead>
        <tr>
          {sessionColumns.map((column) => (
            <Heading key={column.sort} column={column} sortedBy={answer} onSort={onSort} />
          ))}
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
