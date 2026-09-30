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
import { fetchLookup, fetchSessions } from '../api/sessions';
import { Lookup } from '../components/Lookup';
import { SessionTable } from '../components/SessionTable';
import { idToSend } from '../lib/lookup';
import {
  failSessionsRead,
  foldSessionsLine,
  listFilter,
  nextRead,
  readOn,
  type SessionsAnswer,
  type SessionsLine,
} from '../lib/sessions';

interface Reading {
  // What the answer was asked for, as text, so the page can tell an answer for an older ask.
  asked: string;
  answer: SessionsAnswer | null;
  failure: string | null;
}

interface Shown {
  answer: SessionsAnswer | null;
  failure: string | null;
}

function follow(
  ask: string,
  lines: AsyncGenerator<SessionsLine>,
  from: SessionsAnswer | null,
  abort: AbortController,
  set: (reading: Reading) => void,
) {
  let answer = from;

  const fold = async () => {
    for await (const line of lines) {
      answer = foldSessionsLine(answer, line);
      set({ asked: ask, answer, failure: null });
    }
  };

  fold().catch((failure: unknown) => {
    // An abort is the page tidying up after itself, not a failure worth showing.
    if (abort.signal.aborted) {
      return;
    }

    const reason = describeFetchFailure(failure);

    set(
      answer === null
        ? { asked: ask, answer: null, failure: reason }
        : { asked: ask, answer: failSessionsRead(answer, reason), failure: null },
    );
  });
}

// An answer to an older ask would draw its rows under the wrong list.
function shown(reading: Reading | null, ask: string): Shown {
  return reading === null || reading.asked !== ask ? { answer: null, failure: null } : reading;
}

// The newest work first, with nothing asked for, so a reader sees what is happening now the moment the page opens.
export function Sessions() {
  const [reading, setReading] = useState<Reading | null>(null);

  // Kept apart from the list's answer, so clearing the Lookup brings back every row already read.
  const [found, setFound] = useState<Reading | null>(null);

  // Page state and not the address bar, so a link to the list stays a link to the list and a reload clears it.
  const [lookup, setLookup] = useState('');

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

    inFlight.current = abort;

    const later = from === null ? null : nextRead(from);

    // Read back out of the text, so the read depends only on what it is keyed on.
    follow(ask, fetchSessions(readFilter(new URLSearchParams(ask)), abort.signal, later), from, abort, setReading);

    return abort;
  }, []);

  useEffect(() => {
    const abort = read(asked, null);

    // A changed filter stops the old answer, so its rows never land under the new one.
    return () => abort.abort();
  }, [asked, read]);

  const list = shown(reading, asked);

  // Text or null, so a row landing on the list starts no read unless it changes the decision.
  const id = idToSend(list.answer, lookup);

  useEffect(() => {
    if (id === null) {
      return;
    }

    const abort = new AbortController();

    follow(id, fetchLookup(id, abort.signal), null, abort, setFound);

    // A cleared or changed id stops the read, so its row never lands under another id.
    return () => abort.abort();
  }, [id]);

  const lookingUp = id !== null;
  const { answer, failure } = lookingUp ? shown(found, id) : list;

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
        <Lookup text={lookup} onChange={setLookup} />
      </section>

      <ChosenSkill skill={filter.skill} onClear={() => show({ ...filter, skill: '' })} />

      <SessionTable
        answer={answer}
        failure={failure}
        filter={filter}
        lookup={lookup}
        lookingUp={lookingUp}
        onReadOn={() => {
          if (list.answer !== null && readOn(list.answer) === 'ready') {
            read(asked, list.answer);
          }
        }}
      />
    </main>
  );
}
