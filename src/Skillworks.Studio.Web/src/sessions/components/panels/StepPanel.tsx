import { describeCount } from '../../../figures/lib/figures';
import { ranBy, type Depth } from '../../lib/panels/agents';
import { inRange, type Range } from '../../lib/view';
import { describeLength } from '../../../figures/lib/figures';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';

// A View can hold thousands of Steps, and a list that long is no more readable than the timeline above it.
const mostRows = 200;

function Opened({
  mark,
  depth,
  agents,
  onClose,
}: {
  mark: Mark;
  depth: Depth;
  agents: Record<string, string>;
  onClose: () => void;
}) {
  const { step } = mark;
  const note = noteOf(step);

  return (
    <div className="step-open">
      <p className="step-open-head">
        {titleOf(step)}
        {note === null ? null : <span className="step-note">{note}</span>}
        <button type="button" className="step-close" onClick={onClose}>
          Close
        </button>
      </p>
      <p className="micro">
        {describeClock(mark.startMs, true)} · {describeLength(step.lengthMs)} · ran by {ranBy(depth, agents, step.id)}
      </p>
      {step.words === null ? null : <p className="step-words">{step.words}</p>}
    </div>
  );
}

// Every figure and every row here reads the View alone, or the panel would answer a question nobody asked.
export function StepPanel({
  marks,
  depth,
  agents,
  agent,
  view,
  selected,
  onOpen,
}: {
  marks: readonly Mark[];
  depth: Depth;
  agents: Record<string, string>;
  agent: string | null;
  view: Range | null;
  selected: string | null;
  onOpen: (id: string | null) => void;
}) {
  const shown = inRange(marks, view);
  const toolCalls = shown.filter((mark) => mark.step.kind === 'tool').length;
  const faults = shown.filter((mark) => mark.step.fault).length;
  const open = selected === null ? null : (marks.find((mark) => mark.step.id === selected) ?? null);

  return (
    <section className="session-panel" aria-label="Steps">
      <header className="panel-head">
        <h2>Steps</h2>
        <p className="micro panel-figure">
          {describeCount(shown.length)} steps · {describeCount(toolCalls)} tool calls · {describeCount(faults)} faults
          {view === null ? '' : ' in view'}
        </p>
      </header>

      {open === null ? null : <Opened mark={open} depth={depth} agents={agents} onClose={() => onOpen(null)} />}

      {shown.length === 0 ? (
        <p className="session-word">
          {agent === null ? 'Nothing ran in view.' : 'This subagent ran nothing in view.'}
        </p>
      ) : (
        <ol className="step-list">
          {shown.slice(0, mostRows).map((mark) => (
            <li key={mark.step.id}>
              <button
                type="button"
                className={`step-row${mark.step.id === selected ? ' is-open' : ''}`}
                onClick={() => onOpen(mark.step.id)}
              >
                <span className="step-clock">{describeClock(mark.startMs, true)}</span>
                <span className="step-title">{titleOf(mark.step)}</span>
                <span className="step-said">{mark.step.words ?? ''}</span>
                <span className="step-spell">{describeLength(mark.step.lengthMs)}</span>
              </button>
            </li>
          ))}
        </ol>
      )}

      {shown.length > mostRows ? (
        <p className="micro panel-figure">
          The first {describeCount(mostRows)} are listed. Drag across less of the strip to read the rest.
        </p>
      ) : null}
    </section>
  );
}
