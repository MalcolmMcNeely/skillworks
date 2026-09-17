import { describeCount, describeShare, describeTokens } from '../../../figures/lib/figures';
import { inRange, type Range } from '../../lib/brush';
import { ceilingOf, describeInForce, inForceBands, tallyOf, type Level } from '../../lib/panels/context';
import { describeClock } from '../../lib/steps';

function Turn({
  level,
  ceiling,
  open,
  onOpen,
}: {
  level: Level;
  ceiling: number;
  open: boolean;
  onOpen: (step: string) => void;
}) {
  const { point } = level;
  const said = [
    describeClock(level.startMs, true),
    `${describeTokens(point.tokens)} tokens`,
    describeInForce(point),
    ...(point.rebuilt ? [`cache rebuilt, ${describeTokens(point.writtenToCache)} written`] : []),
  ].join(' · ');

  return (
    <li>
      <button
        type="button"
        className={`context-turn${point.rebuilt ? ' is-rebuilt' : ''}${open ? ' is-open' : ''}`}
        aria-label={said}
        title={said}
        onClick={() => onOpen(point.id)}
      >
        <span className="context-fill" style={{ height: `${(point.tokens / ceiling) * 100}%` }} />
      </button>
    </li>
  );
}

// Every bar and every figure here reads the brushed stretch alone, or the panel would answer a question nobody asked.
export function ContextPanel({
  levels,
  limitTokens,
  range,
  selected,
  onOpen,
}: {
  levels: readonly Level[];
  limitTokens: number | null;
  range: Range | null;
  selected: string | null;
  onOpen: (step: string) => void;
}) {
  const shown = inRange(levels, range);
  const tally = tallyOf(shown, limitTokens);
  const ceiling = ceilingOf(shown, limitTokens);
  const bands = inForceBands(shown);

  // Said rather than guessed: a limit no model stated is unknown, and it is never read off the run's own peak.
  const roof =
    limitTokens === null
      ? `${describeTokens(ceiling)} at its peak · limit not known`
      : `${describeTokens(limitTokens)} limit${ceiling > limitTokens ? `, passed at ${describeTokens(ceiling)}` : ''}`;

  return (
    <section className="session-panel" aria-label="Context">
      <header className="panel-head">
        <h2>Context</h2>
        <p className="micro panel-figure">
          {describeCount(tally.turns)} turns · peak {describeTokens(tally.peakTokens)} tokens
          {tally.peakShare === null ? '' : `, ${describeShare(tally.peakShare)} of the limit`} ·{' '}
          {describeCount(tally.rebuilds)} cache rebuilds
          {range === null ? '' : ' in the stretch in view'}
        </p>
      </header>

      {shown.length === 0 ? (
        <p className="session-word">{levels.length === 0 ? 'This run made no turn.' : 'No turn in this stretch.'}</p>
      ) : (
        <div className="context-plot">
          <p className="micro context-roof">{roof}</p>
          <ol className="context-series">
            {shown.map((level) => (
              <Turn
                key={level.point.id}
                level={level}
                ceiling={ceiling}
                open={level.point.id === selected}
                onOpen={onOpen}
              />
            ))}
          </ol>
          <ol className="context-forces">
            {bands.map((band) => (
              <li
                key={`${band.label}-${band.from}`}
                className="context-force"
                style={{ flexGrow: band.to - band.from + 1 }}
                title={`${band.label} in force`}
              >
                {band.label}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
