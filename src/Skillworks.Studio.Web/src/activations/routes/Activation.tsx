import { Fragment, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { describeFetchFailure } from '../../http/lib/errors';
import { describeMoment } from '../../moments/lib/moments';
import { describeDelivery, describeMissingOrigin, describeTrigger } from '../../provenance/lib/provenance';
import { fetchActivation, type ActivationOpened } from '../api/activations';
import { activationsPath, describeRecorded, skillsPath } from '../lib/activations';

export function Activation() {
  const { id = '' } = useParams();
  const [opened, setOpened] = useState<ActivationOpened | null>(null);
  const [activationError, setActivationError] = useState<string | null>(null);

  const [params] = useSearchParams();

  // A link, not a step back, so a firing opened from a bookmark still has a way out to the reader's view.
  const view = params.toString();

  useEffect(() => {
    const abort = new AbortController();

    fetchActivation(id, abort.signal)
      .then((next) => {
        setOpened(next);
        setActivationError(null);
      })
      .catch((failure: unknown) => {
        if (!abort.signal.aborted) {
          setActivationError(describeFetchFailure(failure));
        }
      });

    return () => abort.abort();
  }, [id]);

  const activation = opened?.activation ?? null;

  return (
    <main>
      <p>
        {activation === null ? (
          <Link to={skillsPath(view)}>← Skills</Link>
        ) : (
          <Link to={activationsPath(view, activation.skill)}>← {activation.skill}</Link>
        )}
      </p>

      {activationError !== null && <p data-testid="activation-error">{activationError}</p>}

      {opened !== null && activation !== null && (
        <>
          <h1>{activation.skill}</h1>

          <dl className="activation">
            <dt>When</dt>
            <dd>{describeMoment(activation.timestampUtc)}</dd>

            <dt>Trigger</dt>
            <dd>{describeTrigger(activation.origin?.trigger ?? null)}</dd>

            <dt>Delivered by</dt>
            <dd>
              {activation.origin === null ? 'Not recorded' : describeDelivery(activation.origin)}
            </dd>

            <dt>Model</dt>
            <dd>{describeRecorded(activation.model)}</dd>

            <dt>Effort</dt>
            <dd>{describeRecorded(activation.effort)}</dd>

            <dt>Repository</dt>
            <dd>{describeRecorded(activation.repository)}</dd>

            <dt>Branch</dt>
            <dd>{describeRecorded(activation.branch)}</dd>

            <dt>Session</dt>
            <dd>{describeRecorded(activation.sessionId)}</dd>
          </dl>

          {/* A firing older than the events store, or made with telemetry off, did not come from nowhere. */}
          {activation.origin === null && (
            <p data-testid="provenance-note">{describeMissingOrigin(opened.provenance)}</p>
          )}

          <h2>Arguments</h2>

          {activation.arguments.length === 0 ? (
            <p data-testid="arguments-empty">Nothing was recorded for this activation.</p>
          ) : (
            <dl className="activation arguments">
              {activation.arguments.map((argument) => (
                <Fragment key={argument.name}>
                  <dt>{argument.name}</dt>
                  <dd>{argument.value}</dd>
                </Fragment>
              ))}
            </dl>
          )}
        </>
      )}
    </main>
  );
}
