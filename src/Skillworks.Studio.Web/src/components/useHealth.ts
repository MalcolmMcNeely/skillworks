import { useEffect, useState } from 'react';
import { fetchHealth, type Health } from '../api/health';
import { describeFetchFailure } from '../lib/errors';

/** One read of Studio's health, and whether it has come back yet. */
export interface HealthReading {
  report: Health | null;
  failure: string | null;
  /**
   * False until the first read has either arrived or failed. A screen that explains an empty view
   * has to wait for this: without it, an empty table blames the filter for a moment and then
   * changes its mind, and the first answer is the one a reader acts on.
   */
  settled: boolean;
  /** Asks again, for after the developer has started a container or written a settings file. */
  recheck: () => void;
}

/**
 * Studio's health, read once. Both the panel that shows it and the views that use it to explain an
 * empty screen come through here, so there is one mechanism rather than one per page.
 *
 * It does not poll. Every part of the answer is a question about the outside world — a folder, a
 * container, a settings file — and none of those change without the developer doing something they
 * already know they have done.
 */
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
