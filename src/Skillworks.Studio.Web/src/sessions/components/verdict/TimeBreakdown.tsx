import { describeLength, describeShare } from '../../../shared/figures/lib/figures';
import { notKnown } from '../../lib/sessions';
import {
  breakdownLength,
  noBreakdownWord,
  shareOf,
  sharesOf,
  type Share,
  type TimeBreakdownPage,
} from '../../lib/verdict/timeBreakdown';

function Legend({ share, lengthMs }: { share: Share; lengthMs: number }) {
  return (
    <li className={`breakdown-key${share.known ? '' : ' is-unknown'}`} title={share.note}>
      <span className={`breakdown-dot is-${share.part}`} aria-hidden="true" />
      <span className="breakdown-word">{share.word}</span>
      <span className="breakdown-figure">{share.known ? describeLength(share.ms) : notKnown}</span>
      <span className="breakdown-share">
        {share.known ? describeShare(shareOf(share, lengthMs)) : ''}
        {share.known && share.overlapMs > share.ms ? ` · ${describeLength(share.overlapMs)} in all` : ''}
      </span>
    </li>
  );
}

export function TimeBreakdown({ breakdown }: { breakdown: TimeBreakdownPage | null }) {
  const shares = sharesOf(breakdown, null);
  const lengthMs = breakdownLength(shares);

  return (
    <section className="session-panel" aria-label="Time breakdown">
      <header className="panel-head">
        <h2>Time breakdown</h2>
        <p className="micro panel-figure">{describeLength(lengthMs)} over the whole run</p>
      </header>

      {lengthMs === 0 ? (
        <p className="session-word">{noBreakdownWord(breakdown)}</p>
      ) : (
        <>
          <div className="breakdown-bar" role="img" aria-label="Where the run's time went">
            {shares
              .filter((share) => share.known && share.ms > 0)
              .map((share) => (
                <span
                  key={share.part}
                  className={`breakdown-fill is-${share.part}`}
                  style={{ width: `${shareOf(share, lengthMs) * 100}%` }}
                  title={`${share.word} · ${describeLength(share.ms)}`}
                />
              ))}
          </div>
          <ul className="breakdown-legend">
            {shares.map((share) => (
              <Legend key={share.part} share={share} lengthMs={lengthMs} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
