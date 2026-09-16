// PROTOTYPE — throwaway. Variant A's "where the time went": one bar that adds up to the length, then sums by kind.

import { SessionTip, useTip } from '../SessionTip';
import { format, type TimeKind, type TimePart } from '../sessionMeasures';

export function DrillTime({ parts, kinds, wallMs, scope }: { parts: TimePart[]; kinds: TimeKind[]; wallMs: number; scope: string }) {
  const tip = useTip();
  const shown = parts.filter((part) => part.ms > 0);
  const busy = parts.filter((part) => part.key !== 'yourTurn' && part.key !== 'quiet').reduce((sum, part) => sum + part.ms, 0);
  const kindMax = Math.max(1, wallMs, ...kinds.map((kind) => kind.ms));

  const showPart = (part: TimePart, event: { clientX: number; clientY: number }) =>
    tip.show(
      { title: part.label, when: `${format.duration(part.ms)} · ${format.percent(part.ms / Math.max(1, wallMs))} of ${scope}`, rows: [], said: null, code: part.note, tone: null },
      event,
      null,
    );

  return (
    <section className="drill-frame drill-time" aria-labelledby="drill-time-title">
      <div className="drill-frame-head">
        <h2 id="drill-time-title">Where the time went</h2>
        <span className="drill-sub">{scope}</span>
      </div>

      <dl className="drill-length">
        <div>
          <dt>Start to finish</dt>
          <dd>{format.duration(wallMs)}</dd>
        </div>
        <div>
          <dt>Something running</dt>
          <dd>{format.duration(busy)}</dd>
        </div>
        <div>
          <dt>Busy share</dt>
          <dd>{format.percent(busy / Math.max(1, wallMs))}</dd>
        </div>
      </dl>

      <div className="drill-stack" role="img" aria-label="Each moment of the session, given to one part" onPointerLeave={tip.hide}>
        {shown.map((part) => (
          <span
            key={part.key}
            className={`drill-seg drill-p-${part.key}`}
            style={{ flexGrow: part.ms, flexBasis: 0 }}
            onPointerMove={(event) => showPart(part, event)}
          />
        ))}
      </div>

      <ul className="drill-parts">
        {shown.map((part) => (
          <li key={part.key} onPointerMove={(event) => showPart(part, event)} onPointerLeave={tip.hide}>
            <i className={`drill-p-${part.key}`} />
            <span className="drill-parts-label">{part.label}</span>
            <span className="drill-fig">{format.duration(part.ms)}</span>
            <span className="drill-fig drill-faint">{format.percent(part.ms / Math.max(1, wallMs))}</span>
          </li>
        ))}
      </ul>

      <h3 className="drill-micro">Added up by kind</h3>
      <p className="drill-fine">Parallel work overlaps, so a kind can run longer than the session.</p>
      <dl className="drill-bars">
        {kinds.map((kind) => (
          <div key={kind.key} className="drill-bar-row">
            <dt>{kind.label}</dt>
            <dd className="drill-bar-track">
              <span className="drill-bar-fill" style={{ width: `${(kind.ms / kindMax) * 100}%` }} />
            </dd>
            <dd className="drill-fig">{format.duration(kind.ms)}</dd>
          </div>
        ))}
      </dl>
      <SessionTip tip={tip.tip} />
    </section>
  );
}
