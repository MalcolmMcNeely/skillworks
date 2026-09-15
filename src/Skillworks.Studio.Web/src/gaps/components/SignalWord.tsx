import { noLink } from '../../http/lib/errors';
import { signalOf, type Gap, type Signal } from '../lib/gaps';

export function SignalWord({ gap, failure }: { gap: Gap | null; failure: string | null }) {
  if (gap === null && failure === null) {
    return null;
  }

  const { word, tone }: Signal = gap === null ? { word: noLink, tone: 'failed' } : signalOf(gap.kind);
  const sentence = gap === null ? failure : gap.missing;

  if (sentence === null) {
    return (
      <span className={`signal is-${tone}`}>
        <span className="signal-dot" aria-hidden="true" />
        {word}
      </span>
    );
  }

  // A disclosure, not a tooltip, so the sentence opens by keyboard as well as by click.
  return (
    <details className={`signal is-${tone}`}>
      <summary>
        <span className="signal-dot" aria-hidden="true" />
        {word}
      </summary>
      <p className="signal-sentence">{sentence}</p>
    </details>
  );
}
