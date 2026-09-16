import { useEffect, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router';
import { filterParams, readFilter } from '../../filters/lib/filters';
import { SignalWord } from '../../gaps/components/SignalWord';
import { describeCount, describeMoney } from '../../figures/lib/figures';
import { describeFetchFailure } from '../../http/lib/errors';
import { UpButton } from '../../pages/components/UpButton';
import { useTabTitle } from '../../pages/components/useTabTitle';
import { sessions as page, tabTitleOf } from '../../pages/lib/pages';
import { fetchSession } from '../api/sessions';
import { StepPanel } from '../components/StepPanel';
import { Timeline } from '../components/Timeline';
import { readRange, widened, withRange } from '../lib/brush';
import { describeLength, describeStarted, noRepository, notKnown, readOrder, withOrder } from '../lib/sessions';
import { exchangesOf, foldSessionLine, marksOf, runSpan, type Exchange, type Mark, type Range, type SessionAnswer } from '../lib/steps';
import { readWhere, withWhere, type Where } from '../lib/where';

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
  const range = readRange(params);

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
  const marks = useMemo(() => marksOf(steps ?? []), [steps]);
  const exchanges = useMemo(() => exchangesOf(marks), [marks]);
  const whole = runSpan(marks);

  // Replaced, not pushed, so brushing four stretches does not cost four presses of the back button.
  const write = (written: URLSearchParams) => setParams(written, { replace: true });

  const brush = (stretch: Range | null, exchange: number | null) =>
    write(withRange(withWhere(params, { ...where, exchange }), stretch));

  const open = (step: string | null) => write(withWhere(params, { ...where, step }));

  const onExchange = (exchange: Exchange) =>
    whole === null ? undefined : brush(widened([exchange.startMs, exchange.endMs], whole), exchange.index);

  // What the table was asked for, so going up lands on the list the reader left rather than a fresh one.
  const table = withOrder(filterParams(filter), readOrder(params)).toString();

  return (
    <main className="page session">
      <header className="sessions-head">
        <UpButton parent={page} query={table} />
        <h1>{run?.name ?? 'Run'}</h1>
        {run?.running === true ? <span className="session-running">Running</span> : null}
        <SignalWord gap={answer?.gap ?? null} failure={failure} />
      </header>

      <p className="micro session-crumb">
        {run === null
          ? ''
          : `${run.repository ?? noRepository} · ${run.person ?? notKnown} · ${describeStarted(run.startedUtc)} · ` +
            `${describeLength(run.lengthMs)} · ${describeCount(run.toolCalls)} tool calls · ${describeMoney(run.cost)}`}
      </p>

      <Body
        answer={answer}
        failure={failure}
        marks={marks}
        exchanges={exchanges}
        whole={whole}
        range={range}
        where={where}
        onRange={(stretch) => brush(stretch, stretch === null ? null : where.exchange)}
        onOpen={open}
        onExchange={onExchange}
      />
    </main>
  );
}

function Body({
  answer,
  failure,
  marks,
  exchanges,
  whole,
  range,
  where,
  onRange,
  onOpen,
  onExchange,
}: {
  answer: SessionAnswer | null;
  failure: string | null;
  marks: readonly Mark[];
  exchanges: Exchange[];
  whole: Range | null;
  range: Range | null;
  where: Where;
  onRange: (range: Range | null) => void;
  onOpen: (step: string | null) => void;
  onExchange: (exchange: Exchange) => void;
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
      <Timeline
        marks={marks}
        exchanges={exchanges}
        whole={whole}
        range={range}
        selected={where.step}
        onRange={onRange}
        onOpen={onOpen}
        onExchange={onExchange}
      />
      <StepPanel marks={marks} range={range} selected={where.step} onOpen={onOpen} />
    </>
  );
}
