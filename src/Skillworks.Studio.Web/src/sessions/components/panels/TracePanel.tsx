import { describeCount } from '../../../figures/lib/figures';
import { ranBy, type Depth } from '../../lib/panels/agents';
import { inRange, type Range } from '../../lib/view';
import { notKnown } from '../../lib/sessions';
import { describeLength } from '../../../figures/lib/figures';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';
import { deepestOf, noTreeWord, treeOf } from '../../lib/panels/trace';

// A View can hold thousands of Steps, and a tree that long is no more readable than the timeline above it.
const mostRows = 200;

// Past this the rows would reach the middle of the panel.
const mostIndent = 8;

// Every row and every figure here reads the View alone, or the panel would answer a question nobody asked.
export function TracePanel({
  marks,
  inside,
  depth,
  agents,
  view,
  selected,
  onOpen,
}: {
  marks: readonly Mark[];
  inside: Record<string, string>;
  depth: Depth;
  agents: Record<string, string>;
  view: Range | null;
  selected: string | null;
  onOpen: (id: string | null) => void;
}) {
  // A Thin run has no Span to nest by, so a tree drawn from its Steps alone would be a flat list.
  const shown = depth === 'thin' ? [] : inRange(marks, view);
  const rows = treeOf(shown, inside);

  return (
    <section className="session-panel" aria-label="Trace">
      <header className="panel-head">
        <h2>Trace</h2>
        <p className="micro panel-figure">
          {depth === 'thin' ? (
            notKnown
          ) : (
            <>
              {describeCount(rows.length)} steps · {describeCount(deepestOf(rows))} deep
              {view === null ? '' : ' in view'}
            </>
          )}
        </p>
      </header>

      {rows.length === 0 ? (
        <p className="session-word">{noTreeWord(depth)}</p>
      ) : (
        <ol className="trace-tree">
          {rows.slice(0, mostRows).map((row) => (
            <li key={row.mark.step.id}>
              <button
                type="button"
                className={`trace-row${row.mark.step.id === selected ? ' is-open' : ''}`}
                style={{ paddingLeft: `${0.4 + Math.min(row.level, mostIndent) * 0.9}rem` }}
                onClick={() => onOpen(row.mark.step.id)}
              >
                <span className="trace-title">
                  {titleOf(row.mark.step)}
                  {noteOf(row.mark.step) === null ? null : (
                    <span className="step-note">{noteOf(row.mark.step)}</span>
                  )}
                </span>
                <span className="trace-ran">{ranBy(depth, agents, row.mark.step.id)}</span>
                <span className="trace-clock">{describeClock(row.mark.startMs, true)}</span>
                <span className="trace-spell">{describeLength(row.mark.step.lengthMs)}</span>
              </button>
            </li>
          ))}
        </ol>
      )}

      {rows.length > mostRows ? (
        <p className="micro panel-figure">
          The first {describeCount(mostRows)} are drawn. Drag across less of the strip to read the rest.
        </p>
      ) : null}
    </section>
  );
}
