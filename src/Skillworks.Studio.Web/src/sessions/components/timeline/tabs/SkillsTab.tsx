import { describeCount, describeLength, describeMoney } from '../../../../shared/figures/lib/figures';
import { sameHighlight, type Highlight } from '../../../lib/timeline/highlight';
import type { SkillRow } from '../../../lib/timeline/skills';

function Row({
  row,
  wholeRun,
  lit,
  onPick,
}: {
  row: SkillRow;
  wholeRun: boolean;
  lit: boolean;
  onPick: (picked: Highlight) => void;
}) {
  // Left blank rather than nought, as No skill and Unnamed spend have no Activation.
  const activations = row.activations === null ? '' : describeCount(row.activations);
  const toolCalls = row.toolCalls === null ? 'not known' : describeCount(row.toolCalls);
  const activationWords = row.activations === null ? '' : `${activations} Activations${wholeRun ? ' in the whole run' : ''}, `;

  return (
    <li>
      <button
        type="button"
        className={`skill-row${lit ? ' is-lit' : ''}`}
        aria-pressed={lit}
        aria-label={`${row.label}: ${activationWords}${describeCount(row.turns)} turns, ${toolCalls} tool calls, ${describeMoney(row.cost)}, ${describeLength(row.lengthMs)}`}
        onClick={() => onPick(row.key)}
      >
        <span className={`call-name${row.key.kind === 'skill' ? '' : ' is-unskilled'}`}>{row.label}</span>
        <span className="tool-figure">{activations}</span>
        <span className="tool-figure">{describeCount(row.turns)}</span>
        <span className="tool-figure">{toolCalls}</span>
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
  wholeRun,
  highlight,
  onPick,
}: {
  rows: readonly SkillRow[];
  cost: number;
  inView: boolean;
  // The Activations count alone does not follow an open Subagent.
  wholeRun: boolean;
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
            <span className="tool-figure">
              Activations
              {wholeRun ? <span className="skill-head-note">whole run</span> : null}
            </span>
            <span className="tool-figure">Turns</span>
            <span className="tool-figure">Tool calls</span>
            <span className="tool-figure">Cost</span>
            <span className="tool-figure">Time</span>
          </p>
          <ol className="call-list" aria-label="Skills, most Cost first">
            {rows.map((row) => (
              <Row key={row.label + row.key.kind} row={row} wholeRun={wholeRun} lit={sameHighlight(highlight, row.key)} onPick={onPick} />
            ))}
          </ol>
        </>
      )}
    </>
  );
}
