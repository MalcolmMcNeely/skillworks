import { useEffect, useState } from 'react';
import { describeFetchFailure } from '../../fetching/lib/errors';
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

  // A controller per read rather than one held in state. React remounts a component in development,
  // so a controller that outlived its own cleanup would leave every read after the first aborted
  // before it started — and this panel exists to stop a screen sitting silent.
  useEffect(() => {
    const abort = new AbortController();

    fetchHealth(abort.signal).then(
      (next) => {
        setReport(next);
        setFailure(null);
        setSettled(true);
      },
      (problem: unknown) => {
        // An abort is this effect tidying up after itself, not a failure worth showing. A real
        // failure still settles: a view waiting on health must not wait for ever.
        if (!abort.signal.aborted) {
          setFailure(describeFetchFailure(problem));
          setSettled(true);
        }
      },
    );

    return () => abort.abort();
  }, []);

  // No signal on this one. A click is a deliberate act and the read it starts should finish; there
  // is nothing to abandon it for.
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
