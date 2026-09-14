import { useEffect, useState } from 'react';
import { describeFetchFailure } from '../../fetching/lib/errors';
import {
  fetchFaults,
  fetchIngest,
  fullIngest,
  refreshIngest,
  type IngestStatus,
  type TranscriptFault,
} from '../api/ingest';
import {
  describeFault,
  describeFaultList,
  describeFaults,
  describeIngest,
  describeRefresh,
} from '../lib/ingest';

const pollMilliseconds = 2000;

export function IngestPanel({ onPassFinished }: { onPassFinished: () => void }) {
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [faults, setFaults] = useState<TranscriptFault[] | null>(null);

  // A controller per poll rather than one for the panel's life. React remounts a component in
  // development, so a controller held in state outlives its own cleanup and would leave the panel
  // stuck on "Asking the API…" with nothing to say about why.
  useEffect(() => {
    const abort = new AbortController();
    let told = -1;

    const look = () =>
      fetchIngest(abort.signal).then(
        (next) => {
          setStatus(next);
          setFailure(null);

          // Only when a pass has actually finished, so the rest of the page re-reads once rather
          // than on every poll.
          if (next.completedPasses !== told) {
            told = next.completedPasses;
            onPassFinished();
          }
        },
        (problem: unknown) => {
          // An abort is this effect tidying up after itself, not a failure worth showing.
          if (!abort.signal.aborted) {
            setFailure(describeFetchFailure(problem));
          }
        },
      );

    look();
    const poll = setInterval(look, pollMilliseconds);

    return () => {
      clearInterval(poll);
      abort.abort();
    };
  }, [onPassFinished]);

  // For the reads a click starts. Those carry no signal, because a deliberate act should finish.
  function show(problem: unknown) {
    setFailure(describeFetchFailure(problem));
  }

  function ask(request: () => Promise<IngestStatus>) {
    setFailure(null);

    // The faults on screen belong to the passes already run, so they are dropped rather than left
    // to be read as the answer for the pass that is starting.
    setFaults(null);

    request().then(setStatus, show);
  }

  return (
    <section className="ingest">
      <h2>Ingest</h2>

      {failure !== null && <p data-testid="ingest-error">{failure}</p>}
      {status === null && failure === null && <p>Asking the API…</p>}

      {status !== null && (
        <>
          <p data-testid="ingest-progress">{describeIngest(status)}</p>
          <p data-testid="ingest-refreshed">{describeRefresh(status.lastRefreshUtc)}</p>

          <button type="button" disabled={status.running} onClick={() => ask(refreshIngest)}>
            Look for new sessions
          </button>
          <button type="button" disabled={status.running} onClick={() => ask(fullIngest)}>
            Read everything again
          </button>

          {status.faults > 0 && (
            <>
              <p data-testid="ingest-faults">{describeFaults(status.faults)}</p>

              {faults === null ? (
                <button type="button" onClick={() => fetchFaults().then(setFaults, show)}>
                  Show what was skipped
                </button>
              ) : (
                <>
                  <p>{describeFaultList(faults.length, status.faults)}</p>

                  <ul data-testid="ingest-fault-list">
                    {faults.map((fault) => (
                      <li key={`${fault.path}:${fault.line}`}>{describeFault(fault)}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
