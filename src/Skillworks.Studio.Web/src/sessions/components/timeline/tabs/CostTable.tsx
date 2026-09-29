import { describeLength, describeMoney } from '../../../../shared/figures/lib/figures';
import { skillWordsOf, type CostTurn } from '../../../lib/timeline/cost';
import { describeClock } from '../../../lib/steps';

function Row({ turn, open, onOpen }: { turn: CostTurn; open: boolean; onOpen: (step: string) => void }) {
  const { mark } = turn;
  const ended = describeClock(mark.endMs, true);
  const length = describeLength(mark.endMs - mark.startMs);
  const skill = skillWordsOf(mark.step);

  return (
    <li>
      <button
        type="button"
        className={`cost-turn-row${open ? ' is-open' : ''}`}
        aria-current={open ? 'true' : undefined}
        aria-label={`Ended ${ended}, ${length}, ${skill}, ${describeMoney(mark.step.cost)}, ${describeMoney(turn.soFar)} so far`}
        onClick={() => onOpen(mark.step.id)}
      >
        <span className="tool-figure">{ended}</span>
        <span className="tool-figure">{length}</span>
        <span className="call-name">{skill}</span>
        <span className="tool-figure">{describeMoney(mark.step.cost)}</span>
        <span className="tool-figure">{describeMoney(turn.soFar)}</span>
      </button>
    </li>
  );
}

export function CostTable({
  turns,
  selected,
  onOpen,
}: {
  turns: readonly CostTurn[];
  selected: string | null;
  onOpen: (step: string) => void;
}) {
  return (
    <>
      <p className="cost-turn-heads micro" aria-hidden="true">
        <span className="tool-figure">Ended</span>
        <span className="tool-figure">Time</span>
        <span>Skill</span>
        <span className="tool-figure">Cost</span>
        <span className="tool-figure">So far</span>
      </p>
      <ol className="call-list" aria-label="Turns, in the order they ended">
        {turns.map((turn) => (
          <Row key={turn.mark.step.id} turn={turn} open={turn.mark.step.id === selected} onOpen={onOpen} />
        ))}
      </ol>
    </>
  );
}
