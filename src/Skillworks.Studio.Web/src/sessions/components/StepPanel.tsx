import { describeCount } from '../../figures/lib/figures';
import { holds } from '../lib/brush';
import { describeClock, describeSpell, noteOf, titleOf, type Mark, type Range } from '../lib/steps';

// A stretch can hold thousands of Steps, and a list that long is no more readable than the timeline above it.
const mostRows = 200;

function Opened({ mark, onClose }: { mark: Mark; onClose: () => void }) {
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
        {describeClock(mark.startMs, true)} · {describeSpell(step.lengthMs)}
      </p>
      {step.words === null ? null : <p className="step-words">{step.words}</p>}
    </div>
  );
}

// Every figure and every row here reads the brushed stretch alone, or the panel would answer a question nobody asked.
export function StepPanel({
  marks,
  range,
  selected,
  onOpen,
}: {
  marks: readonly Mark[];
  range: Range | null;
  selected: string | null;
  onOpen: (id: string | null) => void;
}) {
  const shown = marks.filter((mark) => holds(range, mark.startMs, mark.endMs));
  const toolCalls = shown.filter((mark) => mark.step.kind === 'tool').length;
  const faults = shown.filter((mark) => mark.step.fault).length;
  const open = selected === null ? null : (marks.find((mark) => mark.step.id === selected) ?? null);

  return (
    <section className="steps-panel" aria-label="Steps">
      <header className="steps-panel-head">
        <h2>Steps</h2>
        <p className="micro steps-figure">
          {describeCount(shown.length)} steps · {describeCount(toolCalls)} tool calls · {describeCount(faults)} faults
          {range === null ? '' : ' in the stretch in view'}
        </p>
      </header>

      {open === null ? null : <Opened mark={open} onClose={() => onOpen(null)} />}

      {shown.length === 0 ? (
        <p className="session-word">Nothing ran in this stretch.</p>
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
                <span className="step-spell">{describeSpell(mark.step.lengthMs)}</span>
              </button>
            </li>
          ))}
        </ol>
      )}

      {shown.length > mostRows ? (
        <p className="micro steps-figure">
          The first {describeCount(mostRows)} are listed. Brush a shorter stretch to read the rest.
        </p>
      ) : null}
    </section>
  );
}
