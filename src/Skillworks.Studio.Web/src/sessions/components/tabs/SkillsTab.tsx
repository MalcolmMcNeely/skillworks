import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import { sameHighlight, type Highlight } from '../../lib/highlight';
import type { SkillRow } from '../../lib/panels/skills';

function Row({ row, lit, onPick }: { row: SkillRow; lit: boolean; onPick: (picked: Highlight) => void }) {
  // Left blank rather than nought, as No skill and Unnamed spend never fire.
  const fired = row.fired === null ? '' : describeCount(row.fired);

  return (
    <li>
      <button
        type="button"
        className={`skill-row${lit ? ' is-open' : ''}`}
        aria-pressed={lit}
        aria-label={`${row.label}: ${row.fired === null ? '' : `fired ${fired}, `}${describeCount(row.turns)} turns, ${describeCount(row.toolCalls)} tool calls, ${describeMoney(row.cost)}, ${describeLength(row.lengthMs)}`}
        onClick={() => onPick(row.key)}
      >
        <span className={`call-name${row.key.kind === 'skill' ? '' : ' is-unskilled'}`}>{row.label}</span>
        <span className="tool-figure">{fired}</span>
        <span className="tool-figure">{describeCount(row.turns)}</span>
        <span className="tool-figure">{describeCount(row.toolCalls)}</span>
        <span className="tool-figure">{describeMoney(row.cost)}</span>
        <span className="tool-figure">{describeLength(row.lengthMs)}</span>
      </button>
    </li>
  );
}

// Every row and every figure here reads the View alone, or the tab would answer a question nobody asked.
export function SkillsTab({
  rows,
  cost,
  inView,
  highlight,
  onPick,
}: {
  rows: readonly SkillRow[];
  cost: number;
  inView: boolean;
  highlight: Highlight | null;
  onPick: (picked: Highlight) => void;
}) {
  const skills = rows.filter((row) => row.key.kind === 'skill').length;

  return (
    <>
      <header className="panel-head">
        <p className="micro panel-figure">
          {describeCount(skills)} skills · {describeMoney(cost)}
          {inView ? ' in view' : ''}
        </p>
      </header>

      {rows.length === 0 ? (
        <p className="session-word">{inView ? 'No Turn ran in view.' : 'No Turn ran in this run.'}</p>
      ) : (
        <>
          <p className="skill-heads micro" aria-hidden="true">
            <span>Skill</span>
            <span className="tool-figure">Fired</span>
            <span className="tool-figure">Turns</span>
            <span className="tool-figure">Tool calls</span>
            <span className="tool-figure">Cost</span>
            <span className="tool-figure">Time</span>
          </p>
          <ol className="call-list" aria-label="Skills, most Cost first">
            {rows.map((row) => (
              <Row key={row.label + row.key.kind} row={row} lit={sameHighlight(highlight, row.key)} onPick={onPick} />
            ))}
          </ol>
        </>
      )}
    </>
  );
}
