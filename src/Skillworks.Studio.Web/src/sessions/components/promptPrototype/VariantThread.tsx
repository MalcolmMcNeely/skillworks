// PROTOTYPE — throwaway. A: in the thread. The opened Exchange lists its Steps under the Prompt, one line each,
// and the opened Step unfolds where it sits, so the detail reads in the order it happened.
import { useEffect, useRef, useState } from 'react';
import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import type { Band } from '../../lib/timeline/conversation';
import { describeClock, titleOf, toneOf, type Mark } from '../../lib/steps';
import { Drawer, PromptWords } from './Drawer';
import { marksIn, openedOf } from './opened';
import { DetailFull, DetailLine } from './StepCard';

export const name = 'In the thread';

export function VariantThread({
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
  const [pinned, setPinned] = useState(false);
  const open = pinned || opened !== null;
  const list = useRef<HTMLOListElement>(null);
  const current = opened?.band.exchange.index ?? null;

  useEffect(() => {
    document.querySelector('.session')?.classList.toggle('pp-pushed', open);

    return () => document.querySelector('.session')?.classList.remove('pp-pushed');
  }, [open]);

  useEffect(() => {
    const target = step === null ? `[data-exchange="${current}"]` : `[data-step="${step}"]`;

    list.current?.querySelector(target)?.scrollIntoView({ behavior: 'smooth', block: step === null ? 'nearest' : 'center' });
  }, [current, step]);

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
                  <PromptWords words={band.exchange.prompt} length={band.exchange.promptLength} clamp={!isCurrent || step !== null} />
                </button>
                {isCurrent ? (
                  <ol className="pp-thread">
                    {marksIn(marks, bands, band)
                      .filter((mark) => mark.step.kind !== 'prompt')
                      .map((mark) => {
                        const isOpen = mark.step.id === step;

                        return (
                          <li key={mark.step.id} data-step={mark.step.id} className={isOpen ? 'is-open' : ''}>
                            <button
                              type="button"
                              className={`pp-thread-row is-${toneOf(mark.step)}`}
                              aria-expanded={isOpen}
                              onClick={() => onOpen(mark.step.id)}
                            >
                              <span className="pp-thread-time">{describeClock(mark.startMs, true)}</span>
                              <span className="pp-thread-name">{titleOf(mark.step)}</span>
                              <span className="pp-thread-line">
                                <DetailLine mark={mark} />
                              </span>
                            </button>
                            {isOpen ? <DetailFull mark={mark} traced={traced} agents={agents} /> : null}
                          </li>
                        );
                      })}
                  </ol>
                ) : null}
              </li>
            );
          })}
        </ol>
      </Drawer>
    </>
  );
}
