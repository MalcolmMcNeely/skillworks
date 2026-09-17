import { describeShare } from '../../../figures/lib/figures';
import type { Range } from '../../lib/brush';
import { notKnown } from '../../lib/sessions';
import { noSplitWord, shareOf, sharesOf, splitLength, type Share, type SplitPage } from '../../lib/panels/split';
import { describeSpell } from '../../lib/steps';

function Row({ share, lengthMs }: { share: Share; lengthMs: number }) {
  if (!share.known) {
    return (
      <li className="split-row" title={`${share.note} Only a span can say, and this run has none.`}>
        <span className="split-word">{share.word}</span>
        <span className="split-bar" />
        <span className="split-figure">{notKnown}</span>
        <span className="split-share" />
      </li>
    );
  }

  return (
    <li className="split-row" title={share.note}>
      <span className="split-word">{share.word}</span>
      <span className="split-bar">
        <span className="split-fill" style={{ width: `${shareOf(share, lengthMs) * 100}%` }} />
      </span>
      <span className="split-figure">{describeSpell(share.ms)}</span>
      <span className="split-share">
        {describeShare(shareOf(share, lengthMs))}
        {share.overlapMs > share.ms ? ` · ${describeSpell(share.overlapMs)} in all` : ''}
      </span>
    </li>
  );
}

// Every figure here reads the brushed stretch alone, or the panel would answer a question nobody asked.
export function SplitPanel({ split, range }: { split: SplitPage | null; range: Range | null }) {
  const shares = sharesOf(split, range);
  const lengthMs = splitLength(shares);

  return (
    <section className="session-panel" aria-label="Where the time went">
      <header className="panel-head">
        <h2>Where the time went</h2>
        <p className="micro panel-figure">
          {describeSpell(lengthMs)}
          {range === null ? ' over the whole run' : ' in the stretch in view'}
        </p>
      </header>

      {lengthMs === 0 ? (
        <p className="session-word">{noSplitWord(split)}</p>
      ) : (
        <ul className="split-list">
          {shares.map((share) => (
            <Row key={share.part} share={share} lengthMs={lengthMs} />
          ))}
        </ul>
      )}
    </section>
  );
}
