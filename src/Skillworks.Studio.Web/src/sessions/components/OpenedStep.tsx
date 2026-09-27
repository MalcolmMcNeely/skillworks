import { describeLength } from '../../shared/figures/lib/figures';
import { ranBy } from '../lib/panels/agents';
import { describeClock, noteOf, titleOf, type Mark } from '../lib/steps';

export function OpenedStep({
  marks,
  traced,
  agents,
  selected,
  onClose,
}: {
  marks: readonly Mark[];
  traced: boolean;
  agents: Record<string, string>;
  selected: string | null;
  onClose: () => void;
}) {
  const mark = selected === null ? undefined : marks.find((each) => each.step.id === selected);

  if (mark === undefined) {
    return null;
  }

  const { step } = mark;
  const note = noteOf(step);

  return (
    <section className="step-open" aria-label="The opened step">
      <p className="step-open-head">
        {titleOf(step)}
        {note === null ? null : <span className="step-note">{note}</span>}
        <button type="button" className="step-close" onClick={onClose}>
          Close
        </button>
      </p>
      <p className="micro">
        {describeClock(mark.startMs, true)} · {describeLength(step.lengthMs)} · ran by {ranBy(traced, agents, step.id)}
      </p>
      {step.words === null ? null : <p className="step-words">{step.words}</p>}
    </section>
  );
}
