import { useEffect, useMemo, useRef, useState } from 'react';
import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import { ranBy, type Subagent } from '../../lib/timeline/agents';
import type { Band } from '../../lib/timeline/conversation';
import {
  describeUnsaid,
  promptsOf,
  stepRowsOf,
  type Opened,
  type PromptRow,
  type StepRow,
} from '../../lib/timeline/prompts';
import type { Spell } from '../../lib/timeline/view';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';

function keyOf(row: PromptRow): string {
  return row.band === null ? 'before' : String(row.band.exchange.index);
}

function classOf(row: { open: boolean; inView: boolean; started?: boolean }): string | undefined {
  const names = [row.open ? 'is-open' : null, row.inView ? null : 'is-out', row.started === true ? 'is-started' : null].filter(
    (name) => name !== null,
  );

  return names.length === 0 ? undefined : names.join(' ');
}

function Words({ words, length, whole }: { words: string | null; length: number; whole: boolean }) {
  const unsaid = describeUnsaid(words, length);

  // Spans and not paragraphs, as a closed row's Prompt sits inside the button that opens it.
  if (unsaid !== null) {
    return <span className="prompts-unsaid">{unsaid}</span>;
  }

  return <span className={`prompts-words${whole ? '' : ' is-clamped'}`}>{words}</span>;
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

function StepLine({
  row,
  traced,
  agents,
  onStep,
}: {
  row: StepRow;
  traced: boolean;
  agents: Record<string, string>;
  onStep: (step: string) => void;
}) {
  const { mark } = row;
  const { step } = mark;
  const note = noteOf(step);

  return (
    <li data-step={step.id} className={classOf(row)}>
      {row.open ? (
        <OpenedStep mark={mark} traced={traced} agents={agents} />
      ) : (
        <button type="button" className="prompts-step-pick" onClick={() => onStep(step.id)}>
          <span className="micro">{describeClock(mark.startMs, true)}</span>
          <span className="prompts-step-kind">
            {titleOf(step)}
            {note === null ? null : <span className="step-note">{note}</span>}
          </span>
          {row.agent === null ? null : <span className="micro prompts-step-agent">{row.agent}</span>}
          {step.words === null ? null : <span className="prompts-step-words">{step.words}</span>}
        </button>
      )}
    </li>
  );
}

function OpenSubagent({ subagent }: { subagent: Subagent }) {
  return (
    <div className="prompts-subagent">
      <p className="micro">Subagent · {subagent.name}</p>
      {subagent.brief === null || subagent.brief === '' ? (
        <p className="prompts-unsaid">No brief was recorded.</p>
      ) : (
        <p className="prompts-words">{subagent.brief}</p>
      )}
    </div>
  );
}

function Started() {
  return <span className="micro prompts-started">The open Subagent started here</span>;
}

function Row({
  row,
  steps,
  opened,
  traced,
  agents,
  onExchange,
  onStep,
}: {
  row: PromptRow;
  steps: readonly StepRow[];
  opened: Mark | null;
  traced: boolean;
  agents: Record<string, string>;
  onExchange: (band: Band) => void;
  onStep: (step: string) => void;
}) {
  // An Answer, or a Step the lanes have left out, has no row to open in, so it keeps a card of its own.
  const alone = row.open && opened !== null && !steps.some((each) => each.open);
  const step = alone ? <OpenedStep mark={opened} traced={traced} agents={agents} /> : null;
  const list =
    steps.length === 0 ? null : (
      <ol className="prompts-steps">
        {steps.map((each) => (
          <StepLine key={each.mark.step.id} row={each} traced={traced} agents={agents} onStep={onStep} />
        ))}
      </ol>
    );

  if (row.band === null) {
    return (
      <>
        <p className="micro prompts-row-head">Before the first Prompt</p>
        {row.started ? <Started /> : null}
        {step}
        {list}
      </>
    );
  }

  const { band } = row;
  const { exchange, startMs } = band;
  const prompt = <Words words={exchange.prompt} length={exchange.promptLength} whole={row.open} />;

  // The open row's whole Prompt stays outside the button, so a reader can select its words.
  return (
    <>
      <button type="button" className="prompts-pick" onClick={() => onExchange(band)}>
        <span className="micro prompts-row-head">
          {exchange.index + 1} · {describeClock(startMs, true)} · {describeLength(exchange.lengthMs)} ·{' '}
          {describeMoney(exchange.cost)}
        </span>
        {row.started ? <Started /> : null}
        {row.open ? null : prompt}
      </button>
      {row.open ? prompt : null}
      {step}
      {list}
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

// In from the right, so a Step clicked anywhere on the timeline shows the Prompt it answered.
export function Prompts({
  marks,
  bands,
  step,
  exchange,
  prompts,
  view,
  subagent,
  subagents,
  traced,
  agents,
  onExchange,
  onStep,
  onOpen,
  onClose,
}: {
  // Every Step of the run, as the list holds the whole run even with one Subagent open.
  marks: readonly Mark[];
  bands: readonly Band[];
  step: string | null;
  exchange: number | null;
  prompts: boolean;
  view: Spell | null;
  subagent: Subagent | null;
  subagents: readonly Subagent[];
  traced: boolean;
  agents: Record<string, string>;
  onExchange: (band: Band) => void;
  onStep: (step: string) => void;
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

  const rows = useMemo(() => promptsOf(marks, bands, held, view, subagent), [marks, bands, held, view, subagent]);
  const opened = held.step === null ? null : (marks.find((mark) => mark.step.id === held.step) ?? null);
  const openRow = rows.find((row) => row.open);
  const openKey = openRow === undefined ? null : keyOf(openRow);
  const openBand = openRow?.band;
  const steps = useMemo(
    () =>
      openBand === undefined
        ? []
        : stepRowsOf(marks, bands, { band: openBand, step: held.step, view }, { agents, subagents, subagent }),
    [marks, bands, openBand, held.step, view, agents, subagents, subagent],
  );
  const openStep = steps.find((each) => each.open)?.mark.step.id ?? null;

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
    if (!open || openKey === null) {
      return;
    }

    if (openStep === null) {
      list.current?.querySelector(`[data-row="${openKey}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      list.current
        ?.querySelector(`[data-step="${CSS.escape(openStep)}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [open, openKey, openStep]);

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
        {subagent === null ? null : <OpenSubagent subagent={subagent} />}
        {bands.length === 0 ? <p className="prompts-unsaid">No Prompt was recorded for this run.</p> : null}
        <ol className="prompts-list" ref={list}>
          {rows.map((row) => (
            <li key={keyOf(row)} data-row={keyOf(row)} className={classOf(row)}>
              <Row
                row={row}
                steps={row.open ? steps : []}
                opened={opened}
                traced={traced}
                agents={agents}
                onExchange={onExchange}
                onStep={onStep}
              />
            </li>
          ))}
        </ol>
      </aside>
    </>
  );
}
