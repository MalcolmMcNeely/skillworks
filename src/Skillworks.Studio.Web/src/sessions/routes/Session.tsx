import { useEffect, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { filterParams, readFilter } from '../../shared/filters/lib/filters';
import { SignalWord } from '../../shared/gaps/components/SignalWord';
import { describeCount, describeMoney } from '../../shared/figures/lib/figures';
import { describeFetchFailure } from '../../shared/http/lib/errors';
import { UpButton } from '../../shared/pages/components/UpButton';
import { useTabTitle } from '../../shared/pages/components/useTabTitle';
import { sessions as page, tabTitleOf } from '../../shared/pages/lib/pages';
import { fetchSession } from '../api/sessions';
import { DepthWord } from '../components/DepthWord';
import { Findings } from '../components/Findings';
import { ActivationPanel } from '../components/panels/ActivationPanel';
import { ContextPanel } from '../components/panels/ContextPanel';
import { ConversationPanel } from '../components/panels/ConversationPanel';
import { SplitPanel } from '../components/panels/SplitPanel';
import { StepPanel } from '../components/panels/StepPanel';
import { SubagentPanel } from '../components/panels/SubagentPanel';
import { TracePanel } from '../components/panels/TracePanel';
import { Timeline } from '../components/Timeline';
import { rangeOf, readRange, widened, withRange, type Range } from '../lib/view';
import { type Named } from '../lib/findings';
import { activationSpellsOf, type ActivationSpell } from '../lib/panels/activations';
import { agentSpellsOf, ranByOne, type AgentSpell } from '../lib/panels/agents';
import { levelsOf, type Level } from '../lib/panels/context';
import { bandsOf, type Band } from '../lib/panels/conversation';
import { describeRunLength, describeStarted, noRepository, notKnown, readOrder, withOrder } from '../lib/sessions';
import { foldSessionLine, marksOf, runSpan, type Mark, type SessionAnswer } from '../lib/steps';
import { readWhere, withWhere, type Where } from '../../shared/session/lib/where';

interface Reading {
  // The run and the span the answer was asked for, as text, so the page can tell an answer for an older ask.
  asked: string;
  answer: SessionAnswer | null;
  failure: string | null;
}

// Where the reader is lives in the address bar, so an opened run can be linked to and reloaded.
export function Session() {
  const { id = '' } = useParams();
  const [reading, setReading] = useState<Reading | null>(null);
  const [params, setParams] = useSearchParams();

  const filter = readFilter(params);
  const where = readWhere(params);
  const view = readRange(params);

  // Text, as a span read off the address is a new object every render.
  const span = `${filter.from}..${filter.to}`;
  const asked = `${id}?${span}`;

  useEffect(() => {
    const abort = new AbortController();
    // Read back out of the text, so the effect depends only on what it is keyed on.
    const [from, to] = span.split('..');
    const forThis = `${id}?${span}`;

    const read = async () => {
      let answer: SessionAnswer | null = null;

      for await (const line of fetchSession(id, { from, to }, abort.signal)) {
        answer = foldSessionLine(answer, line);
        setReading({ asked: forThis, answer, failure: null });
      }
    };

    read().catch((failure: unknown) => {
      // An abort is the page tidying up after itself, not a failure worth showing.
      if (!abort.signal.aborted) {
        setReading({ asked: forThis, answer: null, failure: describeFetchFailure(failure) });
      }
    });

    return () => abort.abort();
  }, [id, span]);

  const forOlderAsk = reading !== null && reading.asked !== asked;
  const answer = forOlderAsk ? null : (reading?.answer ?? null);
  const failure = forOlderAsk ? null : (reading?.failure ?? null);
  const run = answer?.session ?? null;

  useTabTitle(run === null ? page.tabTitle : tabTitleOf(run.name));

  const steps = answer?.steps;
  const exchanges = answer?.exchanges;
  const activations = answer?.activations;
  const context = answer?.context;
  const subagents = answer?.subagents;
  const marks = useMemo(() => marksOf(steps ?? []), [steps]);
  const bands = useMemo(() => bandsOf(exchanges ?? []), [exchanges]);
  const activationSpells = useMemo(() => activationSpellsOf(activations ?? []), [activations]);
  const levels = useMemo(() => levelsOf(context ?? []), [context]);
  const agentSpells = useMemo(() => agentSpellsOf(subagents ?? []), [subagents]);
  const whole = runSpan(marks);

  // An open Subagent is read like a small Session, so every lane and every row beneath shows its Steps alone.
  const agents = answer?.agents;
  const drawn = useMemo(() => ranByOne(marks, agents ?? {}, where.agent), [marks, agents, where.agent]);

  // Replaced, not pushed, so setting four Views does not cost four presses of the back button.
  const write = (written: URLSearchParams) => setParams(written, { replace: true });

  const show = (shown: Range | null, opened: Partial<Where>) =>
    write(withRange(withWhere(params, { ...where, ...opened }), shown));

  const open = (step: string | null) => write(withWhere(params, { ...where, step }));

  const onExchange = (band: Band) =>
    whole === null ? undefined : show(widened([band.startMs, band.endMs], whole), { exchange: band.exchange.index });

  // Unpadded, unlike an Exchange: one spell abuts the next, and padding would pull that one in too.
  const onActivation = (spell: ActivationSpell) =>
    whole === null
      ? undefined
      : show(rangeOf(spell.atMs, spell.followedToMs, whole), { activation: spell.activation.id });

  const onAgent = (spell: AgentSpell) =>
    whole === null ? undefined : show(widened([spell.startMs, spell.endMs], whole), { agent: spell.agent.id });

  const onFinding = (named: Named) =>
    whole === null ? undefined : show(widened([named.startMs, named.endMs], whole), { step: named.finding.step });

  // What the table was asked for, so going up lands on the list the reader left rather than a fresh one.
  const table = withOrder(filterParams(filter), readOrder(params)).toString();

  return (
    <main className="page session">
      <header className="sessions-head">
        <UpButton parent={page} query={table} />
        <h1>{run?.name ?? 'Run'}</h1>
        {run?.running === true ? <span className="session-running">Running</span> : null}
        <SignalWord gap={answer?.events ?? null} failure={failure} />
        {answer === null ? null : <DepthWord depth={answer.depth} gap={answer.traces} />}
      </header>

      <p className="micro session-crumb">
        {run === null
          ? ''
          : `${run.repository ?? noRepository} · ${run.person ?? notKnown} · ${describeStarted(run.startedUtc)} · ` +
            `${describeRunLength(run.lengthMs)} · ${describeCount(run.toolCalls)} tool calls · ${describeMoney(run.cost)}`}
      </p>

      <Body
        answer={answer}
        failure={failure}
        marks={marks}
        drawn={drawn}
        bands={bands}
        activationSpells={activationSpells}
        levels={levels}
        agentSpells={agentSpells}
        whole={whole}
        view={view}
        where={where}
        onView={(shown) => show(shown, shown === null ? { exchange: null, activation: null, agent: null } : {})}
        onOpen={open}
        onExchange={onExchange}
        onActivation={onActivation}
        onAgent={onAgent}
        onCloseAgent={() => show(null, { agent: null })}
        onFinding={onFinding}
      />
    </main>
  );
}

function Body({
  answer,
  failure,
  marks,
  drawn,
  bands,
  activationSpells,
  levels,
  agentSpells,
  whole,
  view,
  where,
  onView,
  onOpen,
  onExchange,
  onActivation,
  onAgent,
  onCloseAgent,
  onFinding,
}: {
  answer: SessionAnswer | null;
  failure: string | null;
  marks: readonly Mark[];
  drawn: readonly Mark[];
  bands: readonly Band[];
  activationSpells: readonly ActivationSpell[];
  levels: readonly Level[];
  agentSpells: readonly AgentSpell[];
  whole: Range | null;
  view: Range | null;
  where: Where;
  onView: (view: Range | null) => void;
  onOpen: (step: string | null) => void;
  onExchange: (band: Band) => void;
  onActivation: (spell: ActivationSpell) => void;
  onAgent: (spell: AgentSpell) => void;
  onCloseAgent: () => void;
  onFinding: (named: Named) => void;
}) {
  if (failure !== null) {
    return <p className="session-word">{notKnown}</p>;
  }

  if (answer === null || !answer.landed) {
    return <p className="session-word">Reading the run…</p>;
  }

  if (answer.session === null) {
    return <p className="session-word">No run is held under that address.</p>;
  }

  if (whole === null) {
    return <p className="session-word">Nothing was recorded for this run.</p>;
  }

  return (
    <>
      <Findings findings={answer.findings} onOpen={onFinding} />
      <Timeline
        marks={marks}
        drawn={drawn}
        bands={bands}
        whole={whole}
        view={view}
        selected={where.step}
        onView={onView}
        onOpen={onOpen}
        onExchange={onExchange}
      />
      <TracePanel
        marks={drawn}
        inside={answer.inside}
        traced={answer.traced}
        agents={answer.agents}
        view={view}
        selected={where.step}
        onOpen={onOpen}
      />
      <ConversationPanel bands={bands} view={view} opened={where.exchange} onOpen={onExchange} />
      <ActivationPanel spells={activationSpells} view={view} opened={where.activation} onOpen={onActivation} />
      <SubagentPanel
        agentSpells={agentSpells}
        traced={answer.traced}
        view={view}
        opened={where.agent}
        onOpen={onAgent}
        onClose={onCloseAgent}
      />
      <SplitPanel split={answer.split} view={view} />
      <ContextPanel
        levels={levels}
        limitTokens={answer.limitTokens}
        view={view}
        selected={where.step}
        onOpen={onOpen}
      />
      <StepPanel
        marks={drawn}
        traced={answer.traced}
        agents={answer.agents}
        agent={where.agent}
        view={view}
        selected={where.step}
        onOpen={onOpen}
      />
    </>
  );
}
