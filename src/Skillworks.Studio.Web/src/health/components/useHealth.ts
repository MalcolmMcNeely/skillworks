import { useEffect, useState } from 'react';
import { describeFetchFailure } from '../../http/lib/errors';
import { fetchHealth, type Health } from '../api/health';

export interface HealthReading {
  report: Health | null;
  failure: string | null;
  settled: boolean;
  recheck: () => void;
}

export function useHealth(): HealthReading {
  const [report, setReport] = useState<Health | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [settled, setSettled] = useState(false);

  // A controller per read: React remounts in development, so one held in state would abort every later read.
  useEffect(() => {
    const abort = new AbortController();

    fetchHealth(abort.signal).then(
      (next) => {
        setReport(next);
        setFailure(null);
        setSettled(true);
      },
      (problem: unknown) => {
        // An abort is this effect tidying up; a real failure still settles, so no view waits on health for ever.
        if (!abort.signal.aborted) {
          setFailure(describeFetchFailure(problem));
          setSettled(true);
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

  return { report, failure, settled, recheck };
}
