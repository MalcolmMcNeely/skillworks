// PROTOTYPE — throwaway. B: the whole conversation. The drawer pushes the page, so the timeline stays beside it.
import { useEffect, useRef, useState } from 'react';
import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import type { Band } from '../../lib/timeline/conversation';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';
import { Drawer, PromptWords } from './Drawer';
import { openedOf } from './opened';

export const name = 'The conversation';

export function VariantB({
  bands,
  marks,
  step,
  exchange,
  onExchange,
  onClose,
}: {
  bands: readonly Band[];
  marks: readonly Mark[];
  step: string | null;
  exchange: number | null;
  onExchange: (band: Band) => void;
  onClose: () => void;
}) {
  const opened = openedOf(bands, marks, step, exchange);
  const [pinned, setPinned] = useState(false);
  const open = pinned || opened !== null;
  const list = useRef<HTMLOListElement>(null);
  const current = opened?.band.exchange.index ?? null;

  useEffect(() => {
    document.querySelector('.session')?.classList.toggle('pp-pushed', open);

    return () => document.querySelector('.session')?.classList.remove('pp-pushed');
  }, [open]);

  useEffect(() => {
    if (current !== null) {
      list.current?.querySelector(`[data-exchange="${current}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [current]);

  const close = () => {
    setPinned(false);
    onClose();
  };

  return (
    <>
      {open ? null : (
        <button type="button" className="pp-edge" onClick={() => setPinned(true)}>
          Prompts · {bands.length}
        </button>
      )}
      <Drawer open={open} label={`The conversation · ${describeCount(bands.length)} Prompts`} onClose={close}>
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
                  <PromptWords words={band.exchange.prompt} length={band.exchange.promptLength} clamp={!isCurrent} />
                </button>
                {isCurrent && opened?.mark != null ? (
                  <p className="pp-marker">
                    ↳ you opened {titleOf(opened.mark.step)}
                    {noteOf(opened.mark.step) === null ? '' : ` · ${noteOf(opened.mark.step)}`} at{' '}
                    {describeClock(opened.mark.startMs, true)}
                  </p>
                ) : null}
                {isCurrent ? (
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
      </Drawer>
    </>
  );
}
