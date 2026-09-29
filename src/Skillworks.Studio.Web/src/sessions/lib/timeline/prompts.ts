import { describeCount } from '../../../shared/figures/lib/figures';
import { readWhere, withWhere, type Where } from '../../../shared/session/lib/where';
import type { Mark, StepKind } from '../steps';
import { ranByOne, type Subagent } from './agents';
import type { Band } from './conversation';
import { holds, widened, withView, type Spell } from './view';

// A Step answers the last Prompt typed before it, so one after the last Exchange ended still belongs to it.
export function exchangeOf(started: { startMs: number }, bands: readonly Band[]): Band | null {
  let found: Band | null = null;

  for (const band of bands) {
    if (band.startMs <= started.startMs) {
      found = band;
    }
  }

  return found;
}

// A Prompt mark stands for the Exchange it starts, so a click on it opens the Exchange as its band does.
export function exchangeOpenedBy(mark: Mark, bands: readonly Band[]): Band | null {
  return mark.step.kind === 'prompt' ? exchangeOf(mark, bands) : null;
}

export interface PromptRow {
  band: Band | null;
  open: boolean;
  inView: boolean;
  started: boolean;
}

export type Opened = Pick<Where, 'step' | 'exchange'>;

// Every row stays whatever the View, so a reader can move from one Prompt to the next.
export function promptsOf(
  marks: readonly Mark[],
  bands: readonly Band[],
  opened: Opened,
  view: Spell | null,
  subagent: Subagent | null,
): PromptRow[] {
  const open = openOf(marks, bands, opened);
  const startedIn = subagent === null ? undefined : exchangeOf({ startMs: Date.parse(subagent.atUtc) }, bands);
  const rows = bands.map((band) => ({
    band,
    open: open === band,
    inView: holds(view, band.startMs, band.endMs),
    started: startedIn === band,
  }));
  const before = marks.filter((mark) => exchangeOf(mark, bands) === null);

  if (before.length === 0) {
    return rows;
  }

  const inView = before.some((mark) => holds(view, mark.startMs, mark.endMs));

  return [{ band: null, open: open === null, inView, started: startedIn === null }, ...rows];
}

export interface StepRow {
  mark: Mark;
  open: boolean;
  inView: boolean;
  // Null while a Subagent is open, as the drawer names it already.
  agent: string | null;
}

export interface OpenExchange {
  band: Band | null;
  step: string | null;
  view: Spell | null;
}

export interface Agents {
  agents: Record<string, string>;
  subagents: readonly Subagent[];
  subagent: Subagent | null;
}

// The Prompt heads the block and the Answer ends it already, so neither takes a row of its own.
const rowKinds: ReadonlySet<StepKind> = new Set(['turn', 'tool', 'refused', 'fault']);

export function stepRowsOf(
  marks: readonly Mark[],
  bands: readonly Band[],
  open: OpenExchange,
  who: Agents,
): StepRow[] {
  // The Steps the lanes draw, so the drawer never lists what the timeline beside it has left out.
  return ranByOne(marks, who.agents, who.subagent?.id ?? null)
    .filter((mark) => rowKinds.has(mark.step.kind) && exchangeOf(mark, bands) === open.band)
    .toSorted((one, other) => one.startMs - other.startMs)
    .map((mark) => ({
      mark,
      open: mark.step.id === open.step,
      inView: holds(open.view, mark.startMs, mark.endMs),
      agent: who.subagent === null ? agentOf(mark, who) : null,
    }));
}

// Only a Span names an agent, so a Step no Span placed in a Subagent names none rather than the main agent.
function agentOf(mark: Mark, who: Agents): string | null {
  const id = who.agents[mark.step.id];

  if (id === undefined) {
    return null;
  }

  return who.subagents.find((subagent) => subagent.id === id)?.name ?? id;
}

export function describeUnsaid(words: string | null, length: number): string | null {
  if (words !== null && words !== '') {
    return null;
  }

  return length === 0 ? 'Nothing was recorded' : `Withheld · ${describeCount(length)} characters`;
}

// A named Step wins the open row over a named Exchange, so a Step left behind would hold the old row open.
export function openedExchange(params: URLSearchParams, band: Band, whole: Spell): URLSearchParams {
  const where = { ...readWhere(params), exchange: band.exchange.index, step: null };

  return withView(withWhere(params, where), widened([band.startMs, band.endMs], whole));
}

// One write for all three, as any one left behind opens the drawer again on a reload.
export function closedPrompts(params: URLSearchParams): URLSearchParams {
  return withWhere(params, { ...readWhere(params), step: null, exchange: null, prompts: false });
}

// Undefined where no row is open, as null is the row for the Steps from before the first Prompt.
function openOf(marks: readonly Mark[], bands: readonly Band[], opened: Opened): Band | null | undefined {
  if (opened.step !== null) {
    const mark = marks.find((each) => each.step.id === opened.step);

    return mark === undefined ? undefined : exchangeOf(mark, bands);
  }

  return bands.find((band) => band.exchange.index === opened.exchange);
}
