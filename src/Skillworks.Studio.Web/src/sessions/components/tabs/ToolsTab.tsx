import { describeCount, describeLength } from '../../../shared/figures/lib/figures';
import type { Highlight } from '../../lib/highlight';
import type { ToolRow } from '../../lib/panels/tools';

function Row({ row, lit, onPick }: { row: ToolRow; lit: boolean; onPick: (picked: Highlight) => void }) {
  return (
    <li>
      <button
        type="button"
        className={`tool-row${lit ? ' is-open' : ''}`}
        aria-pressed={lit}
        aria-label={`${row.tool}: ${describeCount(row.calls)} calls, ${describeCount(row.faults)} faults, ${describeCount(row.friction)} friction, ${describeLength(row.lengthMs)}`}
        onClick={() => onPick({ kind: 'tool', name: row.tool })}
      >
        <span className="call-name">{row.tool}</span>
        <span className="tool-figure">{describeCount(row.calls)}</span>
        <span className={`tool-figure${row.faults > 0 ? ' is-fault' : ''}`}>{describeCount(row.faults)}</span>
        <span className="tool-figure">{describeCount(row.friction)}</span>
        <span className="tool-figure">{describeLength(row.lengthMs)}</span>
      </button>
    </li>
  );
}

export function ToolsTab({
  rows,
  inView,
  highlight,
  onPick,
}: {
  rows: readonly ToolRow[];
  inView: boolean;
  highlight: Highlight | null;
  onPick: (picked: Highlight) => void;
}) {
  const calls = rows.reduce((sum, row) => sum + row.calls, 0);

  return (
    <>
      <header className="panel-head">
        <p className="micro panel-figure">
          {describeCount(calls)} tool calls · {describeCount(rows.length)} tools
          {inView ? ' in view' : ''}
        </p>
      </header>

      {rows.length === 0 ? (
        <p className="session-word">{inView ? 'No tool was called in view.' : 'No tool was called in this run.'}</p>
      ) : (
        <>
          <p className="tool-heads micro" aria-hidden="true">
            <span>Tool</span>
            <span className="tool-figure">Calls</span>
            <span className="tool-figure">Faults</span>
            <span className="tool-figure">Friction</span>
            <span className="tool-figure">Time</span>
          </p>
          <ol className="call-list" aria-label="Tools, most calls first">
            {rows.map((row) => (
              <Row
                key={row.tool}
                row={row}
                lit={highlight?.kind === 'tool' && highlight.name === row.tool}
                onPick={onPick}
              />
            ))}
          </ol>
        </>
      )}
    </>
  );
}
