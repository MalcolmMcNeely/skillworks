// PROTOTYPE — throwaway. The conversation: every Prompt in a drawer that pushes the page, so the timeline stays beside it.
// It won the first round. The Step detail variants build on it, and T shows it as it was.
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import type { Band } from '../../lib/timeline/conversation';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';
import { Drawer, PromptWords } from './Drawer';
import { openedOf } from './opened';

export function Conversation({
  bands,
  marks,
  step,
  exchange,
  onExchange,
  onClose,
  inspector,
}: {
  bands: readonly Band[];
  marks: readonly Mark[];
  step: string | null;
  exchange: number | null;
  onExchange: (band: Band) => void;
  onClose: () => void;
  // Set where a variant splits the drawer, the Prompts above and the opened Step below.
  inspector?: ReactNode;
}) {
  const opened = openedOf(bands, marks, step, exchange);
  const [pinned, setPinned] = useState(false);
  const open = pinned || opened !== null;
  const list = useRef<HTMLOListElement>(null);
  const current = opened?.band.exchange.index ?? null;
  const split = inspector !== undefined && inspector !== null;

  useEffect(() => {
    const page = document.querySelector('.session');

    page?.classList.toggle('pp-pushed', open && !split);
    page?.classList.toggle('pp-pushed-wide', open && split);

    return () => page?.classList.remove('pp-pushed', 'pp-pushed-wide');
  }, [open, split]);

  useEffect(() => {
    if (current !== null) {
      list.current?.querySelector(`[data-exchange="${current}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [current]);

  const close = () => {
    setPinned(false);
    onClose();
  };

  const prompts = (
    <ol className="pp-conversation" ref={list}>
      {bands.map((band) => {
        const isCurrent = band.exchange.index === current;

        return (
          <li key={band.exchange.index} data-exchange={band.exchange.index} className={isCurrent ? 'is-current' : ''}>
            <button type="button" className="pp-said" onClick={() => onExchange(band)}>
              <span className="micro">
                {band.exchange.index + 1} · {describeClock(band.startMs)} · {describeLength(band.exchange.lengthMs)} ·{' '}
                {describeMoney(band.exchange.cost)}
              </span>
              <PromptWords words={band.exchange.prompt} length={band.exchange.promptLength} clamp={!isCurrent || split} />
            </button>
            {isCurrent && opened?.mark != null ? (
              <p className="pp-marker">
                ↳ you opened {titleOf(opened.mark.step)}
                {noteOf(opened.mark.step) === null ? '' : ` · ${noteOf(opened.mark.step)}`} at{' '}
                {describeClock(opened.mark.startMs, true)}
              </p>
            ) : null}
            {isCurrent && !split ? (
              <div className="pp-reply">
                <p className="micro">
                  {describeCount(band.exchange.turns)} turns · {describeCount(band.exchange.toolCalls)} tool calls, then the answer
                </p>
                <PromptWords words={band.exchange.answer} length={band.exchange.answerLength} />
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );

  return (
    <>
      {open ? null : (
        <button type="button" className="pp-edge" onClick={() => setPinned(true)}>
          Prompts · {bands.length}
        </button>
      )}
      <Drawer open={open} wide={split} label={`The conversation · ${describeCount(bands.length)} Prompts`} onClose={close}>
        {split ? (
          <>
            <div className="pp-split-top">{prompts}</div>
            {inspector}
          </>
        ) : (
          prompts
        )}
      </Drawer>
    </>
  );
}
