import { describeLength, describeShare } from '../../../shared/figures/lib/figures';
import type { Range } from '../../lib/view';
import { notKnown } from '../../lib/sessions';
import {
  breakdownLength,
  noBreakdownWord,
  shareOf,
  sharesOf,
  type Share,
  type TimeBreakdownPage,
} from '../../lib/panels/timeBreakdown';

function Row({ share, lengthMs }: { share: Share; lengthMs: number }) {
  if (!share.known) {
    return (
      <li className="breakdown-row" title={`${share.note} Only a span can say, and this run has none.`}>
        <span className="breakdown-word">{share.word}</span>
        <span className="breakdown-bar" />
        <span className="breakdown-figure">{notKnown}</span>
        <span className="breakdown-share" />
      </li>
    );
  }

  return (
    <li className="breakdown-row" title={share.note}>
      <span className="breakdown-word">{share.word}</span>
      <span className="breakdown-bar">
        <span className="breakdown-fill" style={{ width: `${shareOf(share, lengthMs) * 100}%` }} />
      </span>
      <span className="breakdown-figure">{describeLength(share.ms)}</span>
      <span className="breakdown-share">
        {describeShare(shareOf(share, lengthMs))}
        {share.overlapMs > share.ms ? ` · ${describeLength(share.overlapMs)} in all` : ''}
      </span>
    </li>
  );
}

// Every figure here reads the View alone, or the panel would answer a question nobody asked.
export function TimeBreakdownPanel({ breakdown, view }: { breakdown: TimeBreakdownPage | null; view: Range | null }) {
  const shares = sharesOf(breakdown, view);
  const lengthMs = breakdownLength(shares);

  return (
    <section className="session-panel" aria-label="Time breakdown">
      <header className="panel-head">
        <h2>Time breakdown</h2>
        <p className="micro panel-figure">
          {describeLength(lengthMs)}
          {view === null ? ' over the whole run' : ' in view'}
        </p>
      </header>

      {lengthMs === 0 ? (
        <p className="session-word">{noBreakdownWord(breakdown)}</p>
      ) : (
        <ul className="breakdown-list">
          {shares.map((share) => (
            <Row key={share.part} share={share} lengthMs={lengthMs} />
          ))}
        </ul>
      )}
    </section>
  );
}
