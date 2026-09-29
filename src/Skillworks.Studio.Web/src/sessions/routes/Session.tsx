import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { filterParams, readFilter } from '../../shared/filters/lib/filters';
import { SignalWord } from '../../shared/gaps/components/SignalWord';
import { describeFetchFailure } from '../../shared/wire/lib/errors';
import { UpButton } from '../../shared/pages/components/UpButton';
import { useTabTitle } from '../../shared/pages/components/useTabTitle';
import { sessions as page, tabTitleOf } from '../../shared/pages/lib/pages';
import { fetchSession } from '../api/sessions';
import { DepthWord } from '../components/DepthWord';
import { PromptPrototype } from '../components/promptPrototype/PromptPrototype';
import { Timeline } from '../components/timeline/Timeline';
import { TimelineTabs } from '../components/timeline/tabs/TimelineTabs';
import { CostBreakdown } from '../components/verdict/CostBreakdown';
import { Findings } from '../components/verdict/Findings';
import { Headlines } from '../components/verdict/Headlines';
import { TimeBreakdown } from '../components/verdict/TimeBreakdown';
import { readView, widened, withView, type Spell } from '../lib/timeline/view';
import { type Named } from '../lib/verdict/findings';
import { highlightKey, highlightOf, litBy, readHighlight, toggled, withHighlight, type Highlight } from '../lib/timeline/highlight';
import { activationSpellsOf } from '../lib/timeline/activations';
import { ranByOne } from '../lib/timeline/agents';
import { levelsOf, levelsRanByOne } from '../lib/timeline/context';
import { bandsOf, type Band, type Exchange } from '../lib/timeline/conversation';
import { costIn, skillRowsOf } from '../lib/timeline/skills';
import { toolRowsOf } from '../lib/timeline/tools';
import { describeStarted, listFilter, noRepository, notKnown } from '../lib/sessions';
import { foldSessionLine, marksOf, runSpell, type SessionAnswer } from '../lib/steps';
import { showInTimeline } from '../lib/verdict/showInTimeline';
import { verdictOf, type Verdict } from '../lib/verdict/verdict';
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
  const timeline = useRef<HTMLElement>(null);

  const filter = readFilter(params);
  const where = readWhere(params);
  const view = readView(params);
  const highlight = readHighlight(params);
  // Text, as a Highlight read off the address is a new object every render.
  const litKey = highlight === null ? null : highlightKey(highlight);

  // Text, as a span read off the address is a new object every render.
  const span = `${filter.from}..${filter.to}`;
  const asked = `${id}?${span}`;

  useEffect(() => {
    const abort = new AbortController();
    // Read back out of the text, so the effect depends only on what it is keyed on.
    const cut = span.indexOf('..');
    const from = span.slice(0, cut);
    const to = span.slice(cut + 2);
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
  const marks = useMemo(() => marksOf(steps ?? []), [steps]);
  const bands = useMemo(() => bandsOf(exchanges ?? []), [exchanges]);
  const activationSpells = useMemo(() => activationSpellsOf(activations ?? []), [activations]);
  const levels = useMemo(() => levelsOf(context ?? []), [context]);
  // A new pair every render would make each Finding card work out its moment again.
  const whole = useMemo(() => runSpell(marks), [marks]);

  // An open Subagent is read like a small Session, so every lane shows its Steps alone.
  const agents = answer?.agents;
  const drawn = useMemo(() => ranByOne(marks, agents ?? {}, where.agent), [marks, agents, where.agent]);
  const shownLevels = useMemo(() => levelsRanByOne(levels, agents ?? {}, where.agent), [levels, agents, where.agent]);
  const viewFrom = view?.[0];
  const viewTo = view?.[1];
  const shownView = useMemo<Spell | null>(
    () => (viewFrom === undefined || viewTo === undefined ? null : [viewFrom, viewTo]),
    [viewFrom, viewTo],
  );
  const tools = useMemo(() => toolRowsOf(drawn, shownView), [drawn, shownView]);
  const subagentOpen = where.agent !== null;
  const skills = useMemo(
    () => skillRowsOf(drawn, activationSpells, shownView, subagentOpen),
    [drawn, activationSpells, shownView, subagentOpen],
  );
  const viewCost = useMemo(() => costIn(drawn, shownView), [drawn, shownView]);
  const lit = useMemo(() => {
    const shown = highlightOf(litKey);

    return shown === null ? null : litBy(shown, drawn);
  }, [litKey, drawn]);

  const verdict = useMemo(() => (answer === null ? null : verdictOf(answer)), [answer]);
  const subagents = answer?.subagents;
  const openAgent =
    where.agent === null ? null : (subagents?.find((subagent) => subagent.id === where.agent)?.name ?? where.agent);

  // Replaced, not pushed, so setting four Views does not cost four presses of the back button.
  const write = (written: URLSearchParams) => setParams(written, { replace: true });

  const show = (shown: Spell | null, opened: Partial<Where>) =>
    write(withView(withWhere(params, { ...where, ...opened }), shown));

  const open = (step: string | null) => write(withWhere(params, { ...where, step }));

  const onExchange = (band: Band) =>
    whole === null
      ? undefined
      : show(widened([band.startMs, band.endMs], whole), { exchange: band.exchange.index, step: null });

  // Lights the lanes and nothing more, so the View and every figure stay where the reader left them.
  const onHighlight = (picked: Highlight | null) =>
    write(withHighlight(params, picked === null ? null : toggled(highlight, picked)));

  const toTimeline = () => timeline.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const onFinding = (named: Named) => {
    if (whole !== null) {
      const shown = showInTimeline(named, whole);

      show(shown.view, { step: shown.step });
      toTimeline();
    }
  };

  const onCostExchange = (exchange: Exchange) => {
    const band = bands.find((each) => each.exchange.index === exchange.index);

    if (band !== undefined) {
      onExchange(band);
      toTimeline();
    }
  };

  const onSubagent = (agent: string) => {
    write(withWhere(params, { ...where, agent }));
    toTimeline();
  };

  // What the list was asked for, so going up lands on the list the reader left; the span is the row's own.
  const table = filterParams(listFilter(filter)).toString();

  return (
    <main className="page session">
      <header className="sessions-head">
        <UpButton parent={page} query={table} />
        <h1 className="session-id">Session Id: {id}</h1>
        {run?.running === true ? <span className="session-running">Running</span> : null}
        <SignalWord gap={answer?.events ?? null} failure={failure} />
        {answer === null ? null : <DepthWord depth={answer.depth} gap={answer.traces} />}
      </header>

      <p className="micro session-crumb">
        {run === null
          ? ''
          : `${run.name} · ${run.repository ?? noRepository} · ${run.person ?? notKnown} · ${describeStarted(run.startedUtc)}`}
      </p>

      <Body
        answer={answer}
        failure={failure}
        verdict={verdict}
        whole={whole}
        render={(landed, held, bounds) => (
          <>
            <Headlines headlines={held.headlines} />
            <Findings findings={held.findings} marks={marks} whole={bounds} onShow={onFinding} />
            <div className="verdict-breakdowns">
              <TimeBreakdown breakdown={held.timeBreakdown} />
              <CostBreakdown breakdown={held.costs} onExchange={onCostExchange} onSubagent={onSubagent} />
            </div>
            <Timeline
              ref={timeline}
              marks={marks}
              drawn={drawn}
              bands={bands}
              whole={bounds}
              view={view}
              selected={where.step}
              agent={openAgent}
              highlight={highlight}
              lit={lit}
              onView={(shown) => show(shown, shown === null ? { exchange: null, activation: null, agent: null } : {})}
              onOpen={open}
              onExchange={onExchange}
              onAllAgents={() => write(withWhere(params, { ...where, agent: null }))}
              onClearHighlight={() => onHighlight(null)}
            />
            {/* PROTOTYPE — throwaway: stands in for OpenedStep while the Prompt drawer is judged. */}
            <PromptPrototype
              bands={bands}
              marks={drawn}
              step={where.step}
              exchange={where.exchange}
              highlight={highlight}
              lit={lit}
              traced={landed.traced}
              agents={landed.agents}
              onOpen={open}
              onExchange={onExchange}
              onClose={() => write(withHighlight(withWhere(params, { ...where, step: null, exchange: null }), null))}
            />
            <TimelineTabs
              levels={shownLevels}
              limitTokens={landed.limitTokens}
              skills={skills}
              cost={viewCost}
              tools={tools}
              view={view}
              subagentOpen={subagentOpen}
              selected={where.step}
              highlight={highlight}
              onOpen={open}
              onHighlight={onHighlight}
            />
          </>
        )}
      />
    </main>
  );
}

function Body({
  answer,
  failure,
  verdict,
  whole,
  render,
}: {
  answer: SessionAnswer | null;
  failure: string | null;
  verdict: Verdict | null;
  whole: Spell | null;
  render: (answer: SessionAnswer, verdict: Verdict, whole: Spell) => ReactNode;
}) {
  if (failure !== null) {
    return <p className="session-word">{notKnown}</p>;
  }

  if (answer === null || verdict === null || !answer.landed) {
    return <p className="session-word">Reading the run…</p>;
  }

  if (answer.session === null) {
    return <p className="session-word">No run is held under that address.</p>;
  }

  if (whole === null) {
    return <p className="session-word">Nothing was recorded for this run.</p>;
  }

  return render(answer, verdict, whole);
}
