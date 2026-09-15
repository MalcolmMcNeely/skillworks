import { describeHealth, describePart } from '../lib/health';
import { useHealth } from './useHealth';

export function HealthPanel() {
  const { report, failure, recheck } = useHealth();

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

          {/* Asked for, not polled: only a developer who just started the containers knows it changed. */}
          <button type="button" onClick={recheck}>
            Check again
          </button>
        </>
      )}
    </section>
  );
}
