import type { Headline } from '../../lib/verdict/verdict';

export function Headlines({ headlines }: { headlines: readonly Headline[] }) {
  return (
    <dl className="verdict-headlines" aria-label="The whole run">
      {headlines.map((headline) => (
        <div key={headline.name} className={`verdict-headline${headline.alarm ? ' is-alarm' : ''}`}>
          <dt>{headline.name}</dt>
          <dd className="verdict-figure">{headline.figure}</dd>
          {headline.note === null ? null : <dd className="micro verdict-note">{headline.note}</dd>}
        </div>
      ))}
    </dl>
  );
}
