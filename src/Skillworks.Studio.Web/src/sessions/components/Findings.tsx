import { describeCount } from '../../shared/figures/lib/figures';
import { namedIn, noFindingsWord, type FindingsPage, type Named } from '../lib/findings';

function Row({ named, onOpen }: { named: Named; onOpen: (named: Named) => void }) {
  // Nothing to move to: only a span could have measured this bar and the run has none.
  if (!named.known) {
    return (
      <li className="finding-row is-unknown" title={`${named.note} Only a span can say, and this run has none.`}>
        <span className="finding-word">{named.word}</span>
        <span className="finding-figure">{named.reading}</span>
      </li>
    );
  }

  return (
    <li>
      <button
        type="button"
        className="finding-row"
        title={`${named.note} The bar is ${named.barReading}.`}
        onClick={() => onOpen(named)}
      >
        <span className="finding-word">{named.word}</span>
        <span className="finding-figure">{named.reading}</span>
        <span className="finding-subject">{named.finding.subject ?? ''}</span>
      </button>
    </li>
  );
}

export function Findings({ findings, onOpen }: { findings: FindingsPage | null; onOpen: (named: Named) => void }) {
  const named = namedIn(findings);
  // A row nobody could measure crossed nothing, so counting it would read as trouble the run never had.
  const crossed = named.filter((each) => each.known).length;

  return (
    <section className="session-panel session-findings" aria-label="Findings">
      <header className="panel-head">
        <h2>Findings</h2>
        <p className="micro panel-figure">{crossed === 0 ? '' : `${describeCount(crossed)} crossed a bar`}</p>
      </header>

      {named.length === 0 ? (
        <p className="session-word">{noFindingsWord(findings)}</p>
      ) : (
        <ul className="finding-list">
          {named.map((each) => (
            <Row key={each.kind} named={each} onOpen={onOpen} />
          ))}
        </ul>
      )}
    </section>
  );
}
