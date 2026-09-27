import { useLayoutEffect, useRef, useState, type PointerEvent, type Ref } from 'react';
import type { Spell } from '../../lib/timeline/view';
import { describeLit, type Highlight } from '../../lib/timeline/highlight';
import type { Band } from '../../lib/timeline/conversation';
import { describeLength } from '../../../shared/figures/lib/figures';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';
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
  ref,
  marks,
  drawn,
  bands,
  whole,
  view,
  selected,
  agent,
  highlight,
  lit,
  onView,
  onOpen,
  onExchange,
  onAllAgents,
  onClearHighlight,
}: {
  ref?: Ref<HTMLElement>;
  marks: readonly Mark[];
  // What the lanes draw, which is one Subagent's Steps alone once a reader opens one.
  drawn: readonly Mark[];
  bands: readonly Band[];
  whole: Spell;
  view: Spell | null;
  selected: string | null;
  agent: string | null;
  highlight: Highlight | null;
  lit: ReadonlySet<string> | null;
  onView: (view: Spell | null) => void;
  onOpen: (step: string | null) => void;
  onExchange: (band: Band) => void;
  onAllAgents: () => void;
  onClearHighlight: () => void;
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
    <section className="timeline" aria-label="Timeline" ref={ref}>
      <header className="timeline-head">
        <h2 className="timeline-title">Timeline</h2>
        <p className="micro timeline-readout">
          {view === null
            ? 'The whole run'
            : `${describeClock(view[0], true)} to ${describeClock(view[1], true)} · ${describeLength(view[1] - view[0])}`}
        </p>
        <button type="button" className="timeline-clear" onClick={() => onView(null)} disabled={view === null}>
          Whole run
        </button>
        <p className="micro timeline-hint">Drag across the strip to change what is in view. Click it for the whole run again.</p>
        {agent === null ? null : (
          <>
            <p className="micro timeline-agent">Only the Steps of {agent}</p>
            <button type="button" className="timeline-clear" onClick={onAllAgents}>
              Show all agents
            </button>
          </>
        )}
        {highlight === null ? null : (
          <>
            <p className="micro timeline-lit">Lit: {describeLit(highlight)}</p>
            <button type="button" className="timeline-clear" onClick={onClearHighlight}>
              Clear the highlight
            </button>
          </>
        )}
      </header>

      <div className="timeline-frame" ref={frame}>
        <Overview marks={marks} whole={whole} view={view} left={left} width={width} onView={onView} />
        <Lanes
          marks={drawn}
          bands={bands}
          view={inView}
          selected={selected}
          lit={lit}
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
