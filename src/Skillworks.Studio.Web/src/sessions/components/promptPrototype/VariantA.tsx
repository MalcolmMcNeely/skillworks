// PROTOTYPE — throwaway. A: one Exchange. Any click on the timeline opens the Exchange it sits in.
import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import { ranBy } from '../../lib/timeline/agents';
import type { Band } from '../../lib/timeline/conversation';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';
import { Drawer, PromptWords } from './Drawer';
import { openedOf, useLatch } from './opened';

export const name = 'One Exchange';

export function VariantA({
  bands,
  marks,
  step,
  exchange,
  traced,
  agents,
  onExchange,
  onClose,
}: {
  bands: readonly Band[];
  marks: readonly Mark[];
  step: string | null;
  exchange: number | null;
  traced: boolean;
  agents: Record<string, string>;
  onExchange: (band: Band) => void;
  onClose: () => void;
}) {
  const now = openedOf(bands, marks, step, exchange);
  const shown = useLatch(now);

  const neighbour = (by: number) =>
    shown === null ? undefined : bands.find((band) => band.exchange.index === shown.band.exchange.index + by);
  const before = neighbour(-1);
  const after = neighbour(1);

  return (
    <Drawer open={now !== null} label="The Prompt" onClose={onClose}>
      {shown === null ? null : (
        <div className="pp-body">
          <nav className="pp-nav">
            <button type="button" className="step-close" disabled={before === undefined} onClick={() => before && onExchange(before)}>
              ← Exchange {shown.band.exchange.index}
            </button>
            <p className="pp-title">
              Exchange {shown.band.exchange.index + 1} of {bands.length}
            </p>
            <button type="button" className="step-close" disabled={after === undefined} onClick={() => after && onExchange(after)}>
              Exchange {shown.band.exchange.index + 2} →
            </button>
          </nav>

          <p className="micro">
            {describeClock(shown.band.startMs, true)} · {describeLength(shown.band.exchange.lengthMs)} ·{' '}
            {describeCount(shown.band.exchange.turns)} turns · {describeCount(shown.band.exchange.toolCalls)} tool calls ·{' '}
            {describeMoney(shown.band.exchange.cost)}
          </p>

          {shown.mark === null ? null : (
            <section className="pp-opened">
              <p className="micro">You opened</p>
              <p className="step-open-head">
                {titleOf(shown.mark.step)}
                {noteOf(shown.mark.step) === null ? null : <span className="step-note">{noteOf(shown.mark.step)}</span>}
              </p>
              <p className="micro">
                {describeClock(shown.mark.startMs, true)} · {describeLength(shown.mark.step.lengthMs)} · ran by{' '}
                {ranBy(traced, agents, shown.mark.step.id)}
              </p>
              {shown.mark.step.words === null ? null : <p className="step-words">{shown.mark.step.words}</p>}
            </section>
          )}

          <section>
            <h3 className="pp-heading">Prompt</h3>
            <PromptWords words={shown.band.exchange.prompt} length={shown.band.exchange.promptLength} />
          </section>

          <details className="pp-answer">
            <summary className="pp-heading">Answer</summary>
            <PromptWords words={shown.band.exchange.answer} length={shown.band.exchange.answerLength} />
          </details>
        </div>
      )}
    </Drawer>
  );
}
