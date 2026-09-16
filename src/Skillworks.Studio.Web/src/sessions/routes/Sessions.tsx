import { useEffect, useState } from 'react';
import { everything } from '../../filters/lib/filters';
import { SignalWord } from '../../gaps/components/SignalWord';
import { describeFetchFailure } from '../../http/lib/errors';
import { UpButton } from '../../pages/components/UpButton';
import { useTabTitle } from '../../pages/components/useTabTitle';
import { sessions as page } from '../../pages/lib/pages';
import { fetchSessions } from '../api/sessions';
import { SessionTable } from '../components/SessionTable';
import { describeSpan, foldSessionsLine, type SessionsAnswer } from '../lib/sessions';

interface Reading {
  answer: SessionsAnswer | null;
  failure: string | null;
}

// The whole lookback, with nothing asked for, so a reader sees the organisation's runs the moment the page opens.
export function Sessions() {
  const [reading, setReading] = useState<Reading | null>(null);

  useTabTitle(page.tabTitle);

  useEffect(() => {
    const abort = new AbortController();

    const read = async () => {
      let answer: SessionsAnswer | null = null;

      for await (const line of fetchSessions(everything, abort.signal)) {
        answer = foldSessionsLine(answer, line);
        setReading({ answer, failure: null });
      }
    };

    read().catch((failure: unknown) => {
      // An abort is the page tidying up after itself, not a failure worth showing.
      if (!abort.signal.aborted) {
        setReading({ answer: null, failure: describeFetchFailure(failure) });
      }
    });

    return () => abort.abort();
  }, []);

  const answer = reading?.answer ?? null;

  return (
    <main className="page sessions">
      <header className="sessions-head">
        <UpButton parent={page.parent} />
        <h1>{page.name}</h1>
        <SignalWord gap={answer?.gap ?? null} failure={reading?.failure ?? null} />
      </header>

      <p className="micro sessions-span">
        {answer === null ? 'The lookback' : `${answer.span.lookback ? 'The lookback, ' : ''}${describeSpan(answer.span)}`}
      </p>

      <SessionTable answer={answer} failure={reading?.failure ?? null} />
    </main>
  );
}
