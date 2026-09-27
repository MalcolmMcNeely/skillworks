import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { ChosenSkill } from '../../shared/filters/components/ChosenSkill';
import { RepositoryPicker } from '../../shared/filters/components/RepositoryPicker';
import { everything, filterParams, readFilter, type Filter } from '../../shared/filters/lib/filters';
import { SignalWord } from '../../shared/gaps/components/SignalWord';
import { describeFetchFailure } from '../../shared/wire/lib/errors';
import { UpButton } from '../../shared/pages/components/UpButton';
import { useTabTitle } from '../../shared/pages/components/useTabTitle';
import { sessions as page } from '../../shared/pages/lib/pages';
import { fetchSessions } from '../api/sessions';
import { SessionTable } from '../components/SessionTable';
import { failSessionsRead, foldSessionsLine, listFilter, nextRead, readOn, type SessionsAnswer } from '../lib/sessions';

interface Reading {
  // The filter the answer was asked for, as text, so the page can tell an answer for an older ask.
  asked: string;
  answer: SessionsAnswer | null;
  failure: string | null;
}

// The newest work first, with nothing asked for, so a reader sees what is happening now the moment the page opens.
export function Sessions() {
  const [reading, setReading] = useState<Reading | null>(null);

  // One read at a time, so a changed filter stops a Load more still in flight.
  const inFlight = useRef<AbortController | null>(null);

  useTabTitle(page.tabTitle);

  // The filter lives in the address bar, so a reload, a bookmark or a link lands on the same list.
  const [params, setParams] = useSearchParams();
  const filter = listFilter(readFilter(params));

  // Text, as a filter is a new object every render.
  const asked = filterParams(filter).toString();

  const read = useCallback((ask: string, from: SessionsAnswer | null) => {
    inFlight.current?.abort();

    const abort = new AbortController();
    let answer = from;

    inFlight.current = abort;

    const later = from === null ? null : nextRead(from);

    const lines = async () => {
      // Read back out of the text, so the read depends only on what it is keyed on.
      for await (const line of fetchSessions(readFilter(new URLSearchParams(ask)), abort.signal, later)) {
        answer = foldSessionsLine(answer, line);
        setReading({ asked: ask, answer, failure: null });
      }
    };

    lines().catch((failure: unknown) => {
      // An abort is the page tidying up after itself, not a failure worth showing.
      if (abort.signal.aborted) {
        return;
      }

      const reason = describeFetchFailure(failure);

      setReading(
        answer === null
          ? { asked: ask, answer: null, failure: reason }
          : { asked: ask, answer: failSessionsRead(answer, reason), failure: null },
      );
    });

    return abort;
  }, []);

  useEffect(() => {
    const abort = read(asked, null);

    // A changed filter stops the old answer, so its rows never land under the new one.
    return () => abort.abort();
  }, [asked, read]);

  const forOlderAsk = reading !== null && reading.asked !== asked;
  const answer = forOlderAsk ? null : (reading?.answer ?? null);
  const failure = forOlderAsk ? null : (reading?.failure ?? null);

  // Replaced, not pushed, so trying four narrowings does not cost four presses of the back button.
  const show = (narrowing: Filter) => setParams(filterParams(narrowing), { replace: true });

  return (
    <main className="page sessions">
      <header className="sessions-head">
        <UpButton parent={page.parent} />
        <h1>{page.name}</h1>
        <SignalWord gap={answer?.gap ?? null} failure={failure} />
      </header>

      <section className="sessions-narrow" aria-label="Narrow">
        {/* No span narrows the list, so the Repository choices are those of the lookback. */}
        <RepositoryPicker
          span={everything}
          repository={filter.repository}
          onChange={(repository) => show({ ...filter, repository })}
        />
      </section>

      <ChosenSkill skill={filter.skill} onClear={() => show({ ...filter, skill: '' })} />

      <SessionTable
        answer={answer}
        failure={failure}
        filter={filter}
        onReadOn={() => {
          if (answer !== null && readOn(answer) === 'ready') {
            read(asked, answer);
          }
        }}
      />
    </main>
  );
}
