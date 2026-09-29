import { useEffect, useMemo, useRef, useState } from 'react';
import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import { ranBy } from '../../lib/timeline/agents';
import type { Band } from '../../lib/timeline/conversation';
import { describeUnsaid, promptsOf, type Opened, type PromptRow } from '../../lib/timeline/prompts';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';

function keyOf(row: PromptRow): string {
  return row.band === null ? 'before' : String(row.band.exchange.index);
}

function Words({ words, length, whole }: { words: string | null; length: number; whole: boolean }) {
  const unsaid = describeUnsaid(words, length);

  if (unsaid !== null) {
    return <p className="prompts-unsaid">{unsaid}</p>;
  }

  return <p className={`prompts-words${whole ? '' : ' is-clamped'}`}>{words}</p>;
}

function OpenedStep({ mark, traced, agents }: { mark: Mark; traced: boolean; agents: Record<string, string> }) {
  const { step } = mark;
  const note = noteOf(step);

  return (
    <div className="prompts-step">
      <p className="prompts-step-head">
        {titleOf(step)}
        {note === null ? null : <span className="step-note">{note}</span>}
      </p>
      <p className="micro">
        {describeClock(mark.startMs, true)} · {describeLength(step.lengthMs)} · ran by {ranBy(traced, agents, step.id)}
      </p>
      {step.words === null ? null : <p className="step-words">{step.words}</p>}
    </div>
  );
}

function Row({
  row,
  opened,
  traced,
  agents,
}: {
  row: PromptRow;
  opened: Mark | null;
  traced: boolean;
  agents: Record<string, string>;
}) {
  const step = row.open && opened !== null ? <OpenedStep mark={opened} traced={traced} agents={agents} /> : null;

  if (row.band === null) {
    return (
      <>
        <p className="micro prompts-row-head">Before the first Prompt</p>
        {step}
      </>
    );
  }

  const { exchange, startMs } = row.band;

  return (
    <>
      <p className="micro prompts-row-head">
        {exchange.index + 1} · {describeClock(startMs, true)} · {describeLength(exchange.lengthMs)} ·{' '}
        {describeMoney(exchange.cost)}
      </p>
      <Words words={exchange.prompt} length={exchange.promptLength} whole={row.open} />
      {step}
      {row.open ? (
        <div className="prompts-reply">
          <p className="micro">
            Turns {describeCount(exchange.turns)} · Tool calls {describeCount(exchange.toolCalls)}, then the Answer
          </p>
          <Words words={exchange.answer} length={exchange.answerLength} whole />
        </div>
      ) : null}
    </>
  );
}

// Over the page from the right, so a Step clicked anywhere on the timeline shows the Prompt it answered.
export function Prompts({
  marks,
  bands,
  step,
  exchange,
  prompts,
  traced,
  agents,
  onOpen,
  onClose,
}: {
  // Every Step of the run, as the list holds the whole run even with one Subagent open.
  marks: readonly Mark[];
  bands: readonly Band[];
  step: string | null;
  exchange: number | null;
  prompts: boolean;
  traced: boolean;
  agents: Record<string, string>;
  onOpen: () => void;
  onClose: () => void;
}) {
  const open = step !== null || exchange !== null || prompts;
  const title = `Prompts · ${describeCount(bands.length)}`;
  // What was open last, so the drawer keeps its content while it slides out rather than going blank.
  const [held, setHeld] = useState<Opened>({ step, exchange });
  const list = useRef<HTMLOListElement>(null);

  if (open && (held.step !== step || held.exchange !== exchange)) {
    setHeld({ step, exchange });
  }

  const rows = useMemo(() => promptsOf(marks, bands, held), [marks, bands, held]);
  const opened = held.step === null ? null : (marks.find((mark) => mark.step.id === held.step) ?? null);
  const openRow = rows.find((row) => row.open);
  const openKey = openRow === undefined ? null : keyOf(openRow);

  useEffect(() => {
    if (!open) {
      return;
    }

    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', onKey);

    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open && openKey !== null) {
      list.current?.querySelector(`[data-row="${openKey}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [open, openKey]);

  return (
    <>
      {open ? null : (
        <button type="button" className="prompts-tab" onClick={onOpen}>
          {title}
        </button>
      )}
      <aside className={`prompts${open ? ' is-open' : ''}`} aria-label="Prompts" aria-hidden={!open} inert={!open}>
        <header className="prompts-head">
          <h2 className="prompts-title">{title}</h2>
          <button type="button" className="prompts-close" onClick={onClose}>
            Close · Esc
          </button>
        </header>
        {bands.length === 0 ? <p className="prompts-unsaid">No Prompt was recorded for this run.</p> : null}
        <ol className="prompts-list" ref={list}>
          {rows.map((row) => (
            <li key={keyOf(row)} data-row={keyOf(row)} className={row.open ? 'is-open' : undefined}>
              <Row row={row} opened={opened} traced={traced} agents={agents} />
            </li>
          ))}
        </ol>
      </aside>
    </>
  );
}
