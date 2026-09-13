import { useEffect, useState } from 'react';
import { fetchTelemetry, setTelemetry, type TelemetryState } from '../api/telemetry';
import { describeFetchFailure } from '../lib/errors';
import { describeChange, describeTelemetry } from '../lib/telemetry';

/**
 * The one place telemetry is switched on and off. Nothing is written until the developer has seen
 * the exact change and said yes to it.
 */
export function TelemetrySwitch() {
  const [state, setState] = useState<TelemetryState | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    const abort = new AbortController();

    fetchTelemetry(abort.signal)
      .then(setState)
      .catch((problem: unknown) => {
        // An abort is this effect tidying up after itself, not a failure worth showing.
        if (!abort.signal.aborted) {
          setFailure(describeFetchFailure(problem));
        }
      });

    return () => abort.abort();
  }, []);

  function flip(emitting: boolean) {
    setFailure(null);
    setAsking(false);

    setTelemetry(emitting)
      .then(setState)
      .catch((problem: unknown) => setFailure(describeFetchFailure(problem)));
  }

  return (
    <section className="telemetry">
      <h2>Telemetry</h2>

      {failure !== null && <p data-testid="telemetry-error">{failure}</p>}
      {state === null && failure === null && <p>Asking the API…</p>}

      {state !== null && (
        <>
          <p data-testid="telemetry-status">{describeTelemetry(state)}</p>
          <p>{state.restartNote}</p>

          {state.emitting && (
            <button type="button" onClick={() => flip(false)}>
              Turn telemetry off
            </button>
          )}

          {!state.emitting && state.readable && (
            <>
              <p>
                Turning it on writes these to <code>{state.settingsPath}</code>:
              </p>

              <ul data-testid="telemetry-changes">
                {state.changes.map((change) => (
                  <li key={change.name}>{describeChange(change)}</li>
                ))}
              </ul>

              {asking ? (
                <>
                  <button type="button" onClick={() => flip(true)}>
                    Write them
                  </button>
                  <button type="button" onClick={() => setAsking(false)}>
                    Cancel
                  </button>
                </>
              ) : (
                <button type="button" onClick={() => setAsking(true)}>
                  Turn telemetry on
                </button>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
