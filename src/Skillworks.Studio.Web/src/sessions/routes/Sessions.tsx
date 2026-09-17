import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { ChosenSkill } from '../../filters/components/ChosenSkill';
import { RepositoryPicker } from '../../filters/components/RepositoryPicker';
import { depthKeyOf, depthKeys } from '../../filters/lib/depthKeys';
import { filterParams, readFilter, type Filter } from '../../filters/lib/filters';
import { spanKeyOf, spanKeys, todayUtc, withSpanKey } from '../../filters/lib/spanKeys';
import { SignalWord } from '../../gaps/components/SignalWord';
import { describeFetchFailure } from '../../http/lib/errors';
import { Keys } from '../../keys/components/Keys';
import { UpButton } from '../../pages/components/UpButton';
import { useTabTitle } from '../../pages/components/useTabTitle';
import { sessions as page } from '../../pages/lib/pages';
import { fetchSessions } from '../api/sessions';
import { SessionTable } from '../components/SessionTable';
import {
  describeNoSessions,
  describePeriod,
  foldSessionsLine,
  nextOrder,
  readOrder,
  withOrder,
  type SessionOrder,
  type SessionSort,
  type SessionsAnswer,
} from '../lib/sessions';

interface Reading {
  // The filter and order the answer was asked for, as text, so the page can tell an answer for an older ask.
  asked: string;
  answer: SessionsAnswer | null;
  failure: string | null;
}

// The whole lookback, with nothing asked for, so a reader sees the organisation's runs the moment the page opens.
export function Sessions() {
  const [reading, setReading] = useState<Reading | null>(null);

  useTabTitle(page.tabTitle);

  // The filter and order live in the address bar, so a reload, a bookmark or a link lands on the same table.
  const [params, setParams] = useSearchParams();
  const filter = readFilter(params);
  const order = readOrder(params);

  // Text, as a filter and an order are both new objects every render.
  const asked = withOrder(filterParams(filter), order).toString();

  useEffect(() => {
    const abort = new AbortController();
    // Read back out of the text, so the effect depends only on what it is keyed on.
    const sent = new URLSearchParams(asked);

    const read = async () => {
      let answer: SessionsAnswer | null = null;

      for await (const line of fetchSessions(readFilter(sent), readOrder(sent), abort.signal)) {
        answer = foldSessionsLine(answer, line);
        setReading({ asked, answer, failure: null });
      }
    };

    read().catch((failure: unknown) => {
      // An abort is the page tidying up after itself, not a failure worth showing.
      if (!abort.signal.aborted) {
        setReading({ asked, answer: null, failure: describeFetchFailure(failure) });
      }
    });

    // A changed filter or order stops the old answer, so its rows never land under the new heading.
    return () => abort.abort();
  }, [asked]);

  const forOlderAsk = reading !== null && reading.asked !== asked;
  const answer = forOlderAsk ? null : (reading?.answer ?? null);
  const failure = forOlderAsk ? null : (reading?.failure ?? null);
  const today = todayUtc(new Date());

  // With no dates asked, the answer names the lookback, whose length only the API knows.
  const shownSpan = filter.from !== '' && filter.to !== '' ? filter : (answer?.span ?? null);

  // Replaced, not pushed, so trying four narrowings does not cost four presses of the back button.
  const show = (narrowing: Filter, sorting: SessionOrder) =>
    setParams(withOrder(filterParams(narrowing), sorting), { replace: true });

  return (
    <main className="page sessions">
      <header className="sessions-head">
        <UpButton parent={page.parent} />
        <h1>{page.name}</h1>
        <SignalWord gap={answer?.gap ?? null} failure={failure} />
      </header>

      <section className="sessions-narrow" aria-label="Narrow">
        <Keys
          label="Span"
          pressed={shownSpan === null ? null : spanKeyOf(shownSpan, today)}
          options={spanKeys}
          onPress={(key) => show(withSpanKey(filter, key, today), order)}
        />
        <RepositoryPicker
          span={filter}
          repository={filter.repository}
          onChange={(repository) => show({ ...filter, repository }, order)}
        />
        <Keys
          label="Depth"
          pressed={depthKeyOf(filter)}
          options={depthKeys}
          onPress={(depth) => show({ ...filter, depth }, order)}
        />
        <p className="micro sessions-span">{describePeriod(answer?.span ?? null, shownSpan)}</p>
      </section>

      <ChosenSkill skill={filter.skill} onClear={() => show({ ...filter, skill: '' }, order)} />

      <SessionTable
        answer={answer}
        failure={failure}
        noRuns={describeNoSessions(filter)}
        asked={new URLSearchParams(asked)}
        onSort={(sort: SessionSort) => show(filter, nextOrder(answer, sort))}
      />
    </main>
  );
}
