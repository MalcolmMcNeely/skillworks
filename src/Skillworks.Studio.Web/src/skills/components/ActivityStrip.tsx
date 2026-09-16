import { useEffect, useState, type CSSProperties } from 'react';
import type { SkillsAnswer } from '../lib/answer';
import { describeSlice, nowAt, sliceGlyphs, stripLabels } from '../lib/strip';

const minute = 60 * 1000;

export function ActivityStrip({
  answer,
  failure,
  arriving,
}: {
  answer: SkillsAnswer | null;
  failure: string | null;
  arriving: boolean;
}) {
  const [now, setNow] = useState(() => Date.now());

  // Ticking, so the mark keeps up with the clock between one answer and the next.
  useEffect(() => {
    const ticking = setInterval(() => setNow(Date.now()), minute);

    return () => clearInterval(ticking);
  }, []);

  if (answer === null) {
    // Not busy once the read has failed, or the strip would say an answer is still on its way.
    return <section className="strip is-waiting" aria-label="Activations over the span" aria-busy={failure === null} />;
  }

  const peak = Math.max(1, ...answer.slices.map((slice) => slice.activations ?? 0));
  const at = nowAt(answer.span, now);

  return (
    <section className="strip" aria-label="Activations over the span" aria-busy={arriving}>
      <div className="strip-plot">
        <ol className="slices">
          {answer.slices.map((slice) => (
            <li
              key={`${slice.day}:${slice.startHour}`}
              className={`slice is-${slice.state}${slice.activations === 0 ? ' is-idle' : ''}`}
              style={{ '--level': (slice.activations ?? 0) / peak } as CSSProperties}
            >
              <span className="visually-hidden">{describeSlice(slice)}</span>
              {slice.state === 'missing' && (
                <span className="slice-cross" aria-hidden="true">
                  {sliceGlyphs.missing}
                </span>
              )}
            </li>
          ))}
        </ol>

        {at !== null && (
          <span className="strip-now" style={{ left: `${at * 100}%` }} aria-hidden="true">
            <span className="strip-now-word">Now</span>
          </span>
        )}
      </div>

      <div className="strip-axis" aria-hidden="true">
        {stripLabels(answer.slices).map((label) => (
          <span key={label.at} style={{ left: `${label.at * 100}%` }}>
            {label.text}
          </span>
        ))}
      </div>
    </section>
  );
}
