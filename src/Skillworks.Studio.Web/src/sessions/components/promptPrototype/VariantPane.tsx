// PROTOTYPE — throwaway. B: a pane for the Step. The drawer splits: the Prompts stay above, and the opened Step
// fills the lower half, with a way to walk to the Step before or after it.
import { useEffect } from 'react';
import { describeCount } from '../../../shared/figures/lib/figures';
import type { Band } from '../../lib/timeline/conversation';
import type { Mark } from '../../lib/steps';
import { Conversation } from './Conversation';
import { marksIn, openedOf } from './opened';
import { DetailFull } from './StepCard';

export const name = 'A pane for the Step';

export function VariantPane({
  bands,
  marks,
  step,
  exchange,
  traced,
  agents,
  onOpen,
  onExchange,
  onClose,
}: {
  bands: readonly Band[];
  marks: readonly Mark[];
  step: string | null;
  exchange: number | null;
  traced: boolean;
  agents: Record<string, string>;
  onOpen: (step: string | null) => void;
  onExchange: (band: Band) => void;
  onClose: () => void;
}) {
  const opened = openedOf(bands, marks, step, exchange);
  const mark = opened?.mark ?? null;
  const inside = opened === null ? [] : marksIn(marks, bands, opened.band).filter((each) => each.step.kind !== 'prompt');
  const at = mark === null ? -1 : inside.findIndex((each) => each.step.id === mark.step.id);
  const before = at > 0 ? inside[at - 1] : undefined;
  const after = at >= 0 && at < inside.length - 1 ? inside[at + 1] : undefined;

  // [ and ], as the arrow keys already flip the variants.
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key === '[' && before !== undefined) {
        onOpen(before.step.id);
      } else if (event.key === ']' && after !== undefined) {
        onOpen(after.step.id);
      }
    };

    window.addEventListener('keydown', key);

    return () => window.removeEventListener('keydown', key);
  }, [before, after, onOpen]);

  const pane =
    mark === null || opened === null ? undefined : (
      <section className="pp-pane" aria-label="The opened Step">
        <nav className="pp-nav">
          <button type="button" className="step-close" disabled={before === undefined} onClick={() => before && onOpen(before.step.id)}>
            ← Step before · [
          </button>
          <p className="pp-title">
            Step {describeCount(at + 1)} of {describeCount(inside.length)} · Exchange {opened.band.exchange.index + 1}
          </p>
          <button type="button" className="step-close" disabled={after === undefined} onClick={() => after && onOpen(after.step.id)}>
            ] · Step after →
          </button>
        </nav>
        <DetailFull mark={mark} traced={traced} agents={agents} />
      </section>
    );

  return (
    <Conversation bands={bands} marks={marks} step={step} exchange={exchange} onExchange={onExchange} onClose={onClose} inspector={pane} />
  );
}
