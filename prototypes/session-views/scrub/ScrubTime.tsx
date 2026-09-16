// PROTOTYPE — throwaway. The Where the time went tab, for the stretch in view. The parts share out every moment, so
// they add up to the length; the kinds overlap, as a subagent and the main thread can run at once.

import { memo } from 'react';
import { format, type TimeKind, type TimePart } from '../sessionMeasures';

export const ScrubTime = memo(function ScrubTime({ parts, kinds, wallMs, whole }: { parts: TimePart[]; kinds: TimeKind[]; wallMs: number; whole: boolean }) {
  const total = Math.max(1, wallMs);
  const kindMax = Math.max(total, ...kinds.map((kind) => kind.ms));
  const busy = parts.filter((part) => part.key !== 'yourTurn' && part.key !== 'quiet').reduce((sum, part) => sum + part.ms, 0);

  return (
    <div className="scrub-time">
      <div className="scrub-time-parts">
        <p className="scrub-time-head">
          <span className="scrub-micro">{whole ? 'Whole session' : 'In view'}</span>
          <b>{format.duration(wallMs)}</b>
          <span className="scrub-quiet">
            {format.duration(busy)} with something running · {format.percent(busy / total)}
          </span>
        </p>
        <div className="scrub-stack" role="img" aria-label="Where the time went, as one bar">
          {parts
            .filter((part) => part.ms > 0)
            .map((part) => (
              <i key={part.key} className={`scrub-part-${part.key}`} style={{ flexGrow: part.ms }} title={`${part.label} · ${format.duration(part.ms)}`} />
            ))}
        </div>
        <dl className="scrub-bars">
          {parts.map((part) => (
            <div key={part.key} className={part.ms === 0 ? 'is-zero' : ''} title={part.note}>
              <dt>
                <i className={`scrub-swatch scrub-part-${part.key}`} />
                {part.label}
              </dt>
              <dd className="scrub-bar-track">
                <i className={`scrub-part-${part.key}`} style={{ width: `${(part.ms / total) * 100}%` }} />
              </dd>
              <dd className="scrub-bar-value">
                {format.duration(part.ms)} <span>{format.percent(part.ms / total)}</span>
              </dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="scrub-time-kinds">
        <p className="scrub-time-head">
          <span className="scrub-micro">Added up by kind</span>
          <span className="scrub-quiet">These overlap, so they can pass the length.</span>
        </p>
        <dl className="scrub-bars is-kinds">
          {kinds.map((kind) => (
            <div key={kind.key}>
              <dt>{kind.label}</dt>
              <dd className="scrub-bar-track">
                <i className="scrub-kind" style={{ width: `${(kind.ms / kindMax) * 100}%` }} />
              </dd>
              <dd className="scrub-bar-value">{format.duration(kind.ms)}</dd>
            </div>
          ))}
        </dl>
        <p className="scrub-quiet">Hover a part on the left to read what it counts.</p>
      </div>
    </div>
  );
});
