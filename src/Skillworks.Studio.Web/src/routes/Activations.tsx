import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { fetchActivations, type ActivationList } from '../api/activations';
import { activationPath, describeMoment, describeRecorded, skillsPath } from '../lib/activations';
import { describeFetchFailure } from '../lib/errors';
import { describeEmpty, readFilter } from '../lib/filters';
import { describeProvenance, describeTrigger } from '../lib/provenance';

/**
 * The firings behind one count. The skill comes from the path and the rest of the filter from the
 * address bar, so the list counts exactly what the row that was clicked was counting.
 */
export function Activations() {
  const { skill = '' } = useParams();
  const [activations, setActivations] = useState<ActivationList | null>(null);
  const [activationsError, setActivationsError] = useState<string | null>(null);

  const [params] = useSearchParams();

  // Carried on whole rather than rebuilt, so the sort the reader set on the table is still there
  // when they come back to it.
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
          <p data-testid="provenance-note">{describeProvenance(activations.provenance)}</p>

          {activations.activations.length === 0 ? (
            <p data-testid="activations-empty">{describeEmpty(filter)}</p>
          ) : (
            // Plain rather than virtualised, unlike the skill table. This list is one skill's firings
            // inside a filter, which is hundreds where the table is thousands, and nothing here sorts
            // or re-renders once it has arrived.
            <table className="activations">
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Trigger</th>
                  <th scope="col">Repository</th>
                  <th scope="col">Branch</th>
                  <th scope="col">Model</th>
                  <th scope="col">Effort</th>
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
                    <td>{describeTrigger(activation.origin?.trigger ?? null)}</td>
                    <td>{describeRecorded(activation.repository)}</td>
                    <td>{describeRecorded(activation.branch)}</td>
                    <td>{describeRecorded(activation.model)}</td>
                    <td>{describeRecorded(activation.effort)}</td>
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
