import { useEffect, useRef, useState } from 'react';
import { describeFetchFailure } from '../../http/lib/errors';
import { fetchTelemetry, setTelemetry, type TelemetryState } from '../api/telemetry';
import { describeChange, switchOf, type SwitchReading } from '../lib/telemetry';

function Face({ reading }: { reading: SwitchReading }) {
  return (
    <>
      <span className="switch-glyph" aria-hidden="true">
        ⏻
      </span>
      <span className="switch-word">Telemetry</span>
      <span className="switch-track" aria-hidden="true">
        <span className="switch-knob" />
      </span>
      <span className="switch-mark" aria-hidden="true">
        {reading.mark}
      </span>
    </>
  );
}

export function TelemetrySwitch() {
  const [state, setState] = useState<TelemetryState | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const key = useRef<HTMLButtonElement>(null);

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

  const show = (next: TelemetryState) => {
    setState(next);
    setFailure(null);
  };

  // Back to the switch, or a keyboard user is left on nothing once the box is gone.
  const close = () => {
    setConfirming(false);
    key.current?.focus();
  };

  function flip(emitting: boolean) {
    setTelemetry(emitting).then(show, (problem: unknown) => {
      const refusal = describeFetchFailure(problem);

      // Settings that became unreadable say why themselves; any other refusal would otherwise leave the switch silent.
      fetchTelemetry().then(
        (next) => {
          setState(next);
          setFailure(next.readable ? refusal : null);
        },
        () => setFailure(refusal),
      );
    });
  }

  const reading = switchOf(state, failure);

  // A disclosure, not a tooltip, so why the switch will not flip opens by keyboard as well as by click.
  if (reading.why !== null) {
    return (
      <details className={`switch is-${reading.position}`}>
        <summary>
          <Face reading={reading} />
          <span className="visually-hidden">{reading.word}</span>
        </summary>
        <p className="switch-sentence">{reading.why}</p>
      </details>
    );
  }

  const on = reading.position === 'on';

  return (
    <div className={`switch is-${reading.position}`}>
      <button
        ref={key}
        type="button"
        className="switch-key"
        aria-pressed={on}
        disabled={reading.position === 'asking'}
        onClick={() => (on ? flip(false) : setConfirming((open) => !open))}
      >
        <Face reading={reading} />
      </button>

      {confirming && !on && state !== null && (
        <div
          className="switch-confirm"
          role="group"
          aria-label="Turn telemetry on"
          onKeyDown={(event) => event.key === 'Escape' && close()}
        >
          <span className="micro">Writes</span>
          <code className="switch-path">{state.settingsPath}</code>
          <ul className="switch-changes">
            {state.changes.map((change) => (
              <li key={change.name}>
                <code>{describeChange(change)}</code>
              </li>
            ))}
          </ul>
          <p>{state.restartNote}</p>
          <div className="switch-confirm-keys">
            <button
              type="button"
              className="key is-go"
              onClick={() => {
                flip(true);
                close();
              }}
            >
              <span aria-hidden="true">⏻ </span>On
            </button>
            <button type="button" className="key" onClick={close}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
