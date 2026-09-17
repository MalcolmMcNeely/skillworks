import { useLayoutEffect, useRef, useState, type PointerEvent } from 'react';
import type { Range } from '../lib/view';
import type { Band } from '../lib/panels/conversation';
import { describeLength } from '../../figures/lib/figures';
import { describeClock, noteOf, titleOf, type Mark } from '../lib/steps';
import { Lanes } from './Lanes';
import { Overview } from './Overview';

// Both strips are given the same gutter, so the lane names stand in one column down the whole instrument.
const left = 116;

const leastWidth = 360;

interface Pointed {
  mark: Mark;
  x: number;
  y: number;
}

function useWidth<T extends Element>() {
  const frame = useRef<T>(null);
  const [width, setWidth] = useState(leastWidth);

  useLayoutEffect(() => {
    const node = frame.current;

    if (node === null) {
      return;
    }

    const watching = new ResizeObserver(([entry]) => setWidth(Math.max(leastWidth, Math.round(entry.contentRect.width))));

    watching.observe(node);

    return () => watching.disconnect();
  }, []);

  return [frame, width] as const;
}

// Beside the cursor, so reading what a mark was never moves the run out from under the reader.
function Tip({ pointed }: { pointed: Pointed }) {
  const { step } = pointed.mark;
  const note = noteOf(step);

  return (
    <div className="timeline-tip" style={{ left: pointed.x, top: pointed.y }} role="status">
      <p className="timeline-tip-head">
        {titleOf(step)}
        {note === null ? null : <span className="timeline-tip-note">{note}</span>}
      </p>
      <p className="micro">
        {describeClock(pointed.mark.startMs, true)} · {describeLength(step.lengthMs)}
      </p>
      {step.words === null ? null : <p className="timeline-tip-words">{step.words}</p>}
    </div>
  );
}

export function Timeline({
  marks,
  drawn,
  bands,
  whole,
  view,
  selected,
  onView,
  onOpen,
  onExchange,
}: {
  marks: readonly Mark[];
  // What the lanes draw, which is one Subagent's Steps alone once a reader opens one.
  drawn: readonly Mark[];
  bands: readonly Band[];
  whole: Range;
  view: Range | null;
  selected: string | null;
  onView: (view: Range | null) => void;
  onOpen: (step: string | null) => void;
  onExchange: (band: Band) => void;
}) {
  const [frame, width] = useWidth<HTMLDivElement>();
  const [pointed, setPointed] = useState<Pointed | null>(null);
  const inView = view ?? whole;

  const hover = (mark: Mark | null, event: PointerEvent) => {
    if (mark === null) {
      setPointed(null);

      return;
    }

    const box = frame.current?.getBoundingClientRect();

    setPointed({ mark, x: event.clientX - (box?.left ?? 0) + 14, y: event.clientY - (box?.top ?? 0) + 14 });
  };

  return (
    <section className="timeline" aria-label="Timeline">
      <header className="timeline-head">
        <p className="micro timeline-readout">
          {view === null
            ? 'The whole run'
            : `${describeClock(view[0], true)} to ${describeClock(view[1], true)} · ${describeLength(view[1] - view[0])}`}
        </p>
        <button type="button" className="timeline-clear" onClick={() => onView(null)} disabled={view === null}>
          Whole run
        </button>
        <p className="micro timeline-hint">Drag across the strip to change what is in view. Click it for the whole run again.</p>
      </header>

      <div className="timeline-frame" ref={frame}>
        <Overview marks={marks} whole={whole} view={view} left={left} width={width} onView={onView} />
        <Lanes
          marks={drawn}
          bands={bands}
          view={inView}
          selected={selected}
          left={left}
          width={width}
          onOpen={onOpen}
          onExchange={onExchange}
          onHover={hover}
        />
        {pointed === null ? null : <Tip pointed={pointed} />}
      </div>
    </section>
  );
}
