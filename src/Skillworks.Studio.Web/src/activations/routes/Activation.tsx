import { Fragment, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { describeFetchFailure } from '../../fetching/lib/errors';
import { describeMoment } from '../../moments/lib/moments';
import { describeDelivery, describeMissingOrigin, describeTrigger } from '../../provenance/lib/provenance';
import { fetchActivation, type ActivationOpened } from '../api/activations';
import { activationsPath, describeRecorded, skillsPath } from '../lib/activations';

export function Activation() {
  const { id = '' } = useParams();
  const [opened, setOpened] = useState<ActivationOpened | null>(null);
  const [activationError, setActivationError] = useState<string | null>(null);

  const [params] = useSearchParams();

  // A link rather than a step back through history, so a firing reached from a bookmark or a fresh
  // tab has a way out too. It carries the view along, so the table at the end of it is the one the
  // reader built.
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

            {/* What set this firing off, which is the fact a count cannot carry: a skill the model
                reached for and one a developer had to ask for are not the same success. */}
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

          {/* Why the two rows above may be empty. A firing older than the events store, or one made
              while telemetry was off, is not a firing that came from nowhere. */}
          {activation.origin === null && (
            <p data-testid="provenance-note">{describeMissingOrigin(opened.provenance)}</p>
          )}

          <h2>Arguments</h2>

          {/* Everything the transcript recorded, under the names it recorded them under. A firing
              that carried nothing says so, because that is a fact about it. */}
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
