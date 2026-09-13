import { describeHealth, describePart } from '../lib/health';
import { type HealthReading } from './useHealth';

/**
 * Which parts of Studio are doing their job, in one place. It exists so that an empty screen
 * anywhere else is explained rather than mysterious: the panel names the part that is missing and
 * what a developer would do about it.
 *
 * It renders and nothing else. The route that places it owns the reading, because the same reading
 * is what tells that route why its own table is empty.
 */
export function HealthPanel({ reading }: { reading: HealthReading }) {
  const { report, failure, recheck } = reading;

  return (
    <section className="health">
      <h2>Studio</h2>

      {failure !== null && <p data-testid="health-error">{failure}</p>}
      {report === null && failure === null && <p>Asking the API…</p>}

      {report !== null && (
        <>
          <p data-testid="health-summary">{describeHealth(report.parts)}</p>

          <ul data-testid="health-parts">
            {report.parts.map((part) => (
              <li key={part.name} data-state={part.state}>
                {describePart(part)}
              </li>
            ))}
          </ul>

          {/* Asked for rather than polled. A developer who has just started the containers is the
              only one who knows the answer has changed. */}
          <button type="button" onClick={recheck}>
            Check again
          </button>
        </>
      )}
    </section>
  );
}
