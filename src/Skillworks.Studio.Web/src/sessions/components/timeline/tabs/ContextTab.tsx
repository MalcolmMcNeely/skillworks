import { describeCount, describeShare, describeTokens } from '../../../../shared/figures/lib/figures';
import { inSpell, type Spell } from '../../../lib/timeline/view';
import { ceilingOf, describeInForce, limitNotKnown, tallyOf, type Level } from '../../../lib/timeline/context';
import { describeClock } from '../../../lib/steps';

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

// Every bar and every figure here reads the View alone, or the tab would answer a question nobody asked.
export function ContextTab({
  levels,
  limitTokens,
  view,
  selected,
  onOpen,
}: {
  levels: readonly Level[];
  limitTokens: number | null;
  view: Spell | null;
  selected: string | null;
  onOpen: (step: string) => void;
}) {
  const shown = inSpell(levels, view);
  const tally = tallyOf(shown, limitTokens);
  const ceiling = ceilingOf(shown, limitTokens);

  // Said rather than guessed: a limit no model stated is unknown, and it is never read off the run's own peak.
  const roof =
    limitTokens === null
      ? `${describeTokens(ceiling)} at its peak · ${limitNotKnown}`
      : `${describeTokens(limitTokens)} limit${ceiling > limitTokens ? `, passed at ${describeTokens(ceiling)}` : ''}`;

  return (
    <>
      <header className="panel-head">
        <p className="micro panel-figure">
          {describeCount(tally.turns)} turns · peak {describeTokens(tally.peakTokens)} tokens
          {tally.peakShare === null ? '' : `, ${describeShare(tally.peakShare)} of the limit`} ·{' '}
          {describeCount(tally.rebuilds)} cache rebuilds
          {view === null ? '' : ' in view'}
        </p>
      </header>

      {shown.length === 0 ? (
        <p className="session-word">{levels.length === 0 ? 'This run made no turn.' : 'No turn in view.'}</p>
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
        </div>
      )}
    </>
  );
}
