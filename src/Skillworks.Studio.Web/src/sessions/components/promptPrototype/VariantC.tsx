// PROTOTYPE — throwaway. C: the chain. A Step shows the path from the Prompt to it; a skill or tool row shows the Prompts behind it.
import { useState } from 'react';
import { describeCount, describeLength, describeMoney } from '../../../shared/figures/lib/figures';
import { ranBy } from '../../lib/timeline/agents';
import type { Band } from '../../lib/timeline/conversation';
import { describeLit, type Highlight } from '../../lib/timeline/highlight';
import { describeClock, noteOf, titleOf, type Mark } from '../../lib/steps';
import { Drawer, PromptWords } from './Drawer';
import { bandOf, marksIn, openedOf, useLatch, type Opened } from './opened';

export const name = 'The chain';

// How many Steps lead up to the opened one, so the path fits without a scroll.
const leadUp = 6;

type Shown = { kind: 'opened'; opened: Opened } | { kind: 'lit'; highlight: Highlight; rows: LitRow[] };

interface LitRow {
  band: Band;
  steps: number;
  cost: number;
  faults: number;
}

function Prompt({ band }: { band: Band }) {
  const [whole, setWhole] = useState(false);
  const long = (band.exchange.prompt?.length ?? 0) > 280;

  return (
    <div className="pp-link">
      <p className="micro">
        Prompt · Exchange {band.exchange.index + 1} · {describeClock(band.startMs, true)}
      </p>
      <PromptWords words={band.exchange.prompt} length={band.exchange.promptLength} clamp={long && !whole} />
      {long ? (
        <button type="button" className="pp-more" onClick={() => setWhole(!whole)}>
          {whole ? 'Show less' : 'Show all'}
        </button>
      ) : null}
    </div>
  );
}

function Chain({
  opened,
  bands,
  marks,
  traced,
  agents,
  onOpen,
}: {
  opened: Opened;
  bands: readonly Band[];
  marks: readonly Mark[];
  traced: boolean;
  agents: Record<string, string>;
  onOpen: (step: string) => void;
}) {
  const inside = marksIn(marks, bands, opened.band).filter((mark) => mark.step.kind !== 'prompt');
  const at = opened.mark === null ? -1 : inside.findIndex((mark) => mark.step.id === opened.mark?.step.id);
  const path = opened.mark === null ? [] : inside.slice(Math.max(0, at - leadUp), at);
  const skills = [...new Set(inside.map((mark) => mark.step.skill ?? 'No skill'))];

  return (
    <ol className="pp-chain">
      <li>
        <Prompt band={opened.band} />
      </li>
      <li className="pp-link">
        <p className="micro">Skills in force</p>
        <p className="pp-chips">
          {skills.map((skill) => (
            <span key={skill} className={`pp-chip${opened.mark?.step.skill === skill ? ' is-on' : ''}`}>
              {skill}
            </span>
          ))}
        </p>
      </li>
      {opened.mark === null ? (
        <li className="pp-link">
          <p className="micro">
            What followed · {describeCount(inside.length)} Steps · {describeMoney(opened.band.exchange.cost)}
          </p>
        </li>
      ) : (
        <>
          <li className="pp-link">
            <p className="micro">
              The {describeCount(path.length)} Steps before it{at > leadUp ? ` · ${describeCount(at - leadUp)} earlier not shown` : ''}
            </p>
            <ol className="pp-path">
              {path.map((mark) => (
                <li key={mark.step.id}>
                  <button type="button" onClick={() => onOpen(mark.step.id)} className={mark.step.fault ? 'is-fault' : ''}>
                    <span>{describeClock(mark.startMs, true)}</span>
                    <span>{titleOf(mark.step)}</span>
                    <span className="pp-path-words">{mark.step.words ?? ''}</span>
                  </button>
                </li>
              ))}
            </ol>
          </li>
          <li className="pp-link is-end">
            <p className="micro">You opened</p>
            <p className="step-open-head">
              {titleOf(opened.mark.step)}
              {noteOf(opened.mark.step) === null ? null : <span className="step-note">{noteOf(opened.mark.step)}</span>}
            </p>
            <p className="micro">
              {describeClock(opened.mark.startMs, true)} · {describeLength(opened.mark.step.lengthMs)} · ran by{' '}
              {ranBy(traced, agents, opened.mark.step.id)} · skill {opened.mark.step.skill ?? 'none'}
            </p>
            {opened.mark.step.words === null ? null : <p className="step-words">{opened.mark.step.words}</p>}
          </li>
        </>
      )}
    </ol>
  );
}

export function VariantC({
  bands,
  marks,
  step,
  exchange,
  highlight,
  lit,
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
  highlight: Highlight | null;
  lit: ReadonlySet<string> | null;
  traced: boolean;
  agents: Record<string, string>;
  onOpen: (step: string) => void;
  onExchange: (band: Band) => void;
  onClose: () => void;
}) {
  const opened = openedOf(bands, marks, step, exchange);
  let now: Shown | null = null;

  if (opened !== null) {
    now = { kind: 'opened', opened };
  } else if (highlight !== null && lit !== null) {
    const rows = new Map<number, LitRow>();

    for (const mark of marks) {
      const band = lit.has(mark.step.id) ? bandOf(bands, mark.startMs) : null;

      if (band !== null) {
        const row = rows.get(band.exchange.index) ?? { band, steps: 0, cost: 0, faults: 0 };

        rows.set(band.exchange.index, {
          ...row,
          steps: row.steps + 1,
          cost: row.cost + mark.step.cost,
          faults: row.faults + (mark.step.fault ? 1 : 0),
        });
      }
    }

    now = { kind: 'lit', highlight, rows: [...rows.values()].toSorted((one, other) => other.cost - one.cost) };
  }

  const shown = useLatch(now);

  return (
    <Drawer
      open={now !== null}
      label={shown?.kind === 'lit' ? `The Prompts behind ${describeLit(shown.highlight)}` : 'From the Prompt to the Step'}
      onClose={onClose}
    >
      {shown === null ? null : shown.kind === 'opened' ? (
        <Chain opened={shown.opened} bands={bands} marks={marks} traced={traced} agents={agents} onOpen={onOpen} />
      ) : shown.rows.length === 0 ? (
        <p className="session-word">No Prompt led to these Steps.</p>
      ) : (
        <ol className="pp-conversation">
          {shown.rows.map((row) => (
            <li key={row.band.exchange.index}>
              <button type="button" className="pp-said" onClick={() => onExchange(row.band)}>
                <span className="micro">
                  Exchange {row.band.exchange.index + 1} · {describeCount(row.steps)} lit Steps · {describeMoney(row.cost)}
                  {row.faults > 0 ? ` · ${describeCount(row.faults)} faults` : ''}
                </span>
                <PromptWords words={row.band.exchange.prompt} length={row.band.exchange.promptLength} clamp />
              </button>
            </li>
          ))}
        </ol>
      )}
    </Drawer>
  );
}
