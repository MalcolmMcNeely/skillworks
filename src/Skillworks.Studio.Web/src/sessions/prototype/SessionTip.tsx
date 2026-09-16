// PROTOTYPE — throwaway. One hover card every variant may use, so the high-level details read the same everywhere.

import { useLayoutEffect, useRef, useState } from 'react';
import type { Description } from './sessionMeasures';
import './SessionTip.css';

export interface TipState {
  description: Description;
  x: number;
  y: number;
  hint: string | null;
}

export function useTip() {
  const [tip, setTip] = useState<TipState | null>(null);

  return {
    tip,
    show: (description: Description, event: { clientX: number; clientY: number }, hint: string | null = 'Click for the trace') =>
      setTip({ description, x: event.clientX, y: event.clientY, hint }),
    hide: () => setTip(null),
  };
}

export function SessionTip({ tip }: { tip: TipState | null }) {
  const card = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ left: 0, top: 0 });

  // Measured after layout, so a card near the right or bottom edge flips inward instead of running off the screen.
  useLayoutEffect(() => {
    if (tip === null || card.current === null) return;
    const box = card.current.getBoundingClientRect();
    const left = Math.max(8, Math.min(window.innerWidth - box.width - 10, tip.x + 14));
    const top = tip.y + 16 + box.height > window.innerHeight ? tip.y - box.height - 12 : tip.y + 16;
    setOffset({ left, top: Math.max(8, top) });
  }, [tip]);

  if (tip === null) return null;

  const { description } = tip;

  return (
    <div ref={card} className={`session-tip${description.tone ? ` is-${description.tone}` : ''}`} style={{ transform: `translate(${offset.left}px, ${offset.top}px)` }} role="tooltip">
      <p className="session-tip-title">{description.title}</p>
      <p className="session-tip-when">{description.when}</p>
      {description.rows.length > 0 && (
        <dl>
          {description.rows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {description.code !== null && <code>{description.code}</code>}
      {description.said !== null &&
        (description.said.said.text === null ? (
          <p className="session-tip-withheld">Words withheld · {description.said.said.length.toLocaleString('en-GB')} characters</p>
        ) : (
          <blockquote>{description.said.said.text.length > 280 ? `${description.said.said.text.slice(0, 280)}…` : description.said.said.text}</blockquote>
        ))}
      {tip.hint !== null && <p className="session-tip-hint">{tip.hint}</p>}
    </div>
  );
}
