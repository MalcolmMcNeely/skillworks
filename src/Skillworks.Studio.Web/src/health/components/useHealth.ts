import { useEffect, useState } from 'react';
import { describeFetchFailure } from '../../http/lib/errors';
import { fetchHealth, type Health } from '../api/health';

interface HealthReading {
  report: Health | null;
  failure: string | null;
  recheck: () => void;
}

export function useHealth(): HealthReading {
  const [report, setReport] = useState<Health | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  // A controller per read: React remounts in development, so one held in state would abort every later read.
  useEffect(() => {
    const abort = new AbortController();

    fetchHealth(abort.signal).then(
      (next) => {
        setReport(next);
        setFailure(null);
      },
      (problem: unknown) => {
        // An abort is this effect tidying up, not a failure worth showing.
        if (!abort.signal.aborted) {
          setFailure(describeFetchFailure(problem));
        }
      },
    );

    return () => abort.abort();
  }, []);

  // No signal: a click is a deliberate act, and the read it starts should finish.
  const recheck = () => {
    fetchHealth().then(
      (next) => {
        setReport(next);
        setFailure(null);
      },
      (problem: unknown) => setFailure(describeFetchFailure(problem)),
    );
  };

  return { report, failure, recheck };
}
