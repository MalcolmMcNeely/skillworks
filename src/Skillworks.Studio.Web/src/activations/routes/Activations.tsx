import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { describeEmpty, describeSpan, readFilter } from '../../filters/lib/filters';
import { GapNote } from '../../gaps/components/GapNote';
import { explainsEmpty } from '../../gaps/lib/gaps';
import { describeFetchFailure } from '../../http/lib/errors';
import { describeMoment } from '../../moments/lib/moments';
import { describeDelivery, describeTrigger } from '../../provenance/lib/provenance';
import { fetchActivations, type ActivationList } from '../api/activations';
import { activationPath, describeRecorded, skillsPath } from '../lib/activations';

export function Activations() {
  const { skill = '' } = useParams();
  const [activations, setActivations] = useState<ActivationList | null>(null);
  const [activationsError, setActivationsError] = useState<string | null>(null);

  const [params] = useSearchParams();

  // Carried on whole, so the sort the reader set on the table is still there when they come back.
  const view = params.toString();
  const filter = { ...readFilter(params), skill };

  useEffect(() => {
    const abort = new AbortController();

    fetchActivations({ ...readFilter(new URLSearchParams(view)), skill }, abort.signal)
      .then((next) => {
        setActivations(next);
        setActivationsError(null);
      })
      .catch((failure: unknown) => {
        if (!abort.signal.aborted) {
          setActivationsError(describeFetchFailure(failure));
        }
      });

    return () => abort.abort();
  }, [view, skill]);

  return (
    <main>
      <p>
        <Link to={skillsPath(view)}>← Skills</Link>
      </p>

      <h1>{skill}</h1>

      {activationsError !== null && <p data-testid="activations-error">{activationsError}</p>}

      {activations !== null && (
        <>
          <p data-testid="activations-span">Covers {describeSpan(activations.span)}.</p>

          <GapNote gap={activations.gap} />

          {activations.activations.length === 0 ? (
            !explainsEmpty(activations.gap.kind) && (
              <p data-testid="activations-empty">{describeEmpty(filter)}</p>
            )
          ) : (
            // Plain, not virtualised: one skill's firings in a filter run to hundreds, and nothing here sorts.
            <table className="activations">
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Trigger</th>
                  <th scope="col">Delivered by</th>
                  <th scope="col">Session</th>
                  <th scope="col">Repository</th>
                </tr>
              </thead>
              <tbody>
                {activations.activations.map((activation) => (
                  <tr key={activation.id}>
                    <td>
                      {/* The moment is the link, because it is what tells two firings apart. */}
                      <Link to={activationPath(view, activation.id)}>
                        {describeMoment(activation.timestampUtc)}
                      </Link>
                    </td>
                    <td>{describeTrigger(activation.origin.trigger)}</td>
                    <td>{describeDelivery(activation.origin)}</td>
                    <td>{describeRecorded(activation.sessionId)}</td>
                    <td>{describeRecorded(activation.repository)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </main>
  );
}
