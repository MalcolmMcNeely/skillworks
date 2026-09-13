import { Fragment, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { fetchActivation, type ActivationDetail } from '../api/activations';
import { activationsPath, describeMoment, describeRecorded, skillsPath } from '../lib/activations';
import { describeFetchFailure } from '../lib/errors';

/**
 * One firing, opened. This is the view that turns a count into evidence: it names what the skill
 * was asked to do, and the terms it ran on, so a reader can judge whether it fired for a reason.
 */
export function Activation() {
  const { id = '' } = useParams();
  const [activation, setActivation] = useState<ActivationDetail | null>(null);
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
        setActivation(next);
        setActivationError(null);
      })
      .catch((failure: unknown) => {
        if (!abort.signal.aborted) {
          setActivationError(describeFetchFailure(failure));
        }
      });

    return () => abort.abort();
  }, [id]);

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

      {activation !== null && (
        <>
          <h1>{activation.skill}</h1>

          <dl className="activation">
            <dt>When</dt>
            <dd>{describeMoment(activation.timestampUtc)}</dd>

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
