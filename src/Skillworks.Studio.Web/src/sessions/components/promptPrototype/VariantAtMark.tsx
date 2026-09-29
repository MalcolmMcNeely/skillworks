// PROTOTYPE — throwaway. C: on the timeline. The tip beside the cursor says what a mark did, a click pins the whole
// of it under the mark, and the drawer keeps to the Prompts.
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useSearchParams } from 'react-router';
import type { Band } from '../../lib/timeline/conversation';
import type { Mark } from '../../lib/steps';
import { Conversation } from './Conversation';
import { DetailBrief, DetailFull } from './StepCard';

export const name = 'On the timeline';

const cardPx = 560;

interface Place {
  frame: Element;
  markX: number;
  markBottom: number;
  top: number;
  width: number;
}

// Measured every frame, as a View change or a resize moves the mark and nothing tells the card.
function usePlace(): Place | null {
  const [place, setPlace] = useState<Place | null>(null);

  useEffect(() => {
    let frameId = 0;

    const measure = () => {
      const frame = document.querySelector('.timeline-frame');
      const lanes = frame?.querySelector('.timeline-lanes');
      const mark = lanes?.querySelector('.timeline-mark.is-open');

      if (frame && lanes && mark) {
        const at = frame.getBoundingClientRect();
        const box = mark.getBoundingClientRect();
        const next = {
          frame,
          markX: box.left + box.width / 2 - at.left,
          markBottom: box.bottom - at.top,
          top: lanes.getBoundingClientRect().bottom - at.top + 4,
          width: at.width,
        };

        setPlace((last) =>
          last !== null &&
          last.frame === next.frame &&
          last.markX === next.markX &&
          last.markBottom === next.markBottom &&
          last.top === next.top &&
          last.width === next.width
            ? last
            : next,
        );
      } else {
        setPlace((last) => (last === null ? last : null));
      }

      frameId = requestAnimationFrame(measure);
    };

    frameId = requestAnimationFrame(measure);

    return () => cancelAnimationFrame(frameId);
  }, []);

  return place;
}

function Pinned({
  mark,
  traced,
  agents,
  onOpen,
}: {
  mark: Mark;
  traced: boolean;
  agents: Record<string, string>;
  onOpen: (step: string | null) => void;
}) {
  const place = usePlace();

  if (place === null) {
    return null;
  }

  const left = Math.max(0, Math.min(place.width - cardPx, place.markX - 90));

  return createPortal(
    <>
      <span className="pp-pin-stem" style={{ left: place.markX, top: place.markBottom, height: place.top - place.markBottom }} />
      <section className="pp-pin" style={{ left, top: place.top, width: cardPx }} aria-label="The pinned Step">
        <button type="button" className="step-close pp-pin-close" onClick={() => onOpen(null)}>
          Unpin
        </button>
        <DetailFull mark={mark} traced={traced} agents={agents} />
      </section>
    </>,
    place.frame,
  );
}

export function VariantAtMark({
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
  const mark = step === null ? undefined : marks.find((each) => each.step.id === step);

  return (
    <>
      <Conversation bands={bands} marks={marks} step={step} exchange={exchange} onExchange={onExchange} onClose={onClose} />
      {mark === undefined ? null : <Pinned mark={mark} traced={traced} agents={agents} onOpen={onOpen} />}
    </>
  );
}

// Read by the timeline's own tip, which adds these lines only while C is the variant shown.
export function PrototypeTip({ mark }: { mark: Mark }) {
  const [params] = useSearchParams();

  if ((params.get('variant') ?? 'A') !== 'C' || (mark.step.kind !== 'turn' && mark.step.kind !== 'tool')) {
    return null;
  }

  return (
    <div className="pp-tip-extra">
      <DetailBrief mark={mark} />
    </div>
  );
}
