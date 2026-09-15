import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { GapNote } from '../../gaps/components/GapNote';
import { describeFetchFailure } from '../../http/lib/errors';
import { describeMoment } from '../../moments/lib/moments';
import { describeDelivery, describeTrigger } from '../../provenance/lib/provenance';
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

      {/* Outside the firing, as an unreadable events store leaves no firing to show it beside. */}
      {opened !== null && <GapNote gap={opened.gap} />}

      {activation !== null && (
        <>
          <h1>{activation.skill}</h1>

          <dl className="activation">
            <dt>When</dt>
            <dd>{describeMoment(activation.timestampUtc)}</dd>

            <dt>Trigger</dt>
            <dd>{describeTrigger(activation.origin.trigger)}</dd>

            <dt>Delivered by</dt>
            <dd>{describeDelivery(activation.origin)}</dd>

            <dt>Repository</dt>
            <dd>{describeRecorded(activation.repository)}</dd>

            <dt>Session</dt>
            <dd>{describeRecorded(activation.sessionId)}</dd>
          </dl>
        </>
      )}
    </main>
  );
}
