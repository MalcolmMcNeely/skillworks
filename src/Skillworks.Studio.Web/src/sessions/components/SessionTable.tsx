import { Link } from 'react-router';
import { describeCount, describeMoney } from '../../figures/lib/figures';
import { nowhere, sessionAddress } from '../../shared/session/lib/where';
import {
  describeRunLength,
  describeStarted,
  measureWords,
  noRepository,
  notKnown,
  sessionColumns,
  sortGlyphs,
  takesOrder,
  type DrawnSession,
  type Measured,
  type SessionColumn,
  type SessionSort,
  type SessionsAnswer,
  type SortedBy,
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

function Row({ row, asked }: { row: DrawnSession; asked: URLSearchParams }) {
  const { session, measures } = row;

  return (
    <tr>
      <td className="session-started">{describeStarted(session.startedUtc)}</td>
      <td>{session.repository ?? noRepository}</td>
      <td>{session.person ?? notKnown}</td>
      <td className="session-name">
        <Link to={sessionAddress(session.id, nowhere, asked)}>{session.name}</Link>
        {session.running ? <span className="session-running">Running</span> : null}
      </td>
      <td className="session-figure">{describeRunLength(session.lengthMs)}</td>
      <Cell measured={measures.toolCalls} describe={describeCount} />
      <Cell measured={measures.cost} describe={describeMoney} />
      <Cell measured={measures.faults} describe={describeCount} />
    </tr>
  );
}

// The mark comes from the answer, never from what was asked, so a heading never claims an order that did not happen.
function Heading({
  column,
  sortedBy,
  takes,
  onSort,
}: {
  column: SessionColumn;
  sortedBy: SortedBy;
  takes: boolean;
  onSort: (sort: SessionSort) => void;
}) {
  const sorted = sortedBy.sort === column.sort;
  const glyph = sortedBy.descending ? sortGlyphs.descending : sortGlyphs.ascending;

  return (
    <th scope="col" aria-sort={sorted ? (sortedBy.descending ? 'descending' : 'ascending') : 'none'}>
      <button type="button" className="session-sort" disabled={!takes} onClick={() => onSort(column.sort)}>
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
  noRuns,
  asked,
  onSort,
}: {
  answer: SessionsAnswer | null;
  failure: string | null;
  noRuns: string;
  // What the table was asked for, so a run opens with the span and the order a reader can come back to.
  asked: URLSearchParams;
  onSort: (sort: SessionSort) => void;
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
      <caption className="visually-hidden">Sessions, sorted on any column</caption>
      <thead>
        <tr>
          {sessionColumns.map((column) => (
            <Heading
              key={column.sort}
              column={column}
              sortedBy={answer}
              takes={takesOrder(answer, column)}
              onSort={onSort}
            />
          ))}
        </tr>
      </thead>
      <tbody>
        {answer.rows.map((row) => (
          <Row key={row.session.id} row={row} asked={asked} />
        ))}
      </tbody>
    </table>
  );
}
