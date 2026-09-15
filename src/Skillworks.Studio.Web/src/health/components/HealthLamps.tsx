import { lampsOf, type Lamp } from '../lib/health';
import { useHealth } from './useHealth';

function HealthLamp({ lamp }: { lamp: Lamp }) {
  const face = (
    <>
      <span className="lamp-glyph" aria-hidden="true">
        {lamp.glyph}
      </span>
      {lamp.callSign}
      <span className="visually-hidden">{lamp.word}</span>
    </>
  );

  if (lamp.opens === null) {
    return <li className={`lamp is-${lamp.state}`}>{face}</li>;
  }

  // A disclosure, not a tooltip, so the detail and the action open by keyboard as well as by click.
  // One name, so opening a second lamp closes the first rather than stacking its sentence over it.
  return (
    <li className={`lamp is-${lamp.state}`}>
      <details name="lamps">
        <summary>{face}</summary>
        <div className="lamp-sentence">
          <p>{lamp.opens.detail}</p>
          {lamp.opens.action !== null && <p>{lamp.opens.action}</p>}
        </div>
      </details>
    </li>
  );
}

export function HealthLamps() {
  const { report, failure, checking, recheck } = useHealth();

  return (
    <div className="lamps">
      <ul aria-label="Health">
        {lampsOf(report, failure).map((lamp) => (
          <HealthLamp key={lamp.callSign} lamp={lamp} />
        ))}
      </ul>

      {/* Asked for, not polled: only a developer who just started the containers knows it changed. */}
      <button type="button" className="recheck" aria-label="Check Health again" aria-busy={checking} onClick={recheck}>
        <span aria-hidden="true">↻</span>
      </button>
    </div>
  );
}
