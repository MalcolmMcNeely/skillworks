import type { Gap } from '../../gaps/lib/gaps';
import { depthTone, describeDepth, type Depth } from '../lib/panels/agents';

// Drawn from the moment the head lands, not when the answer ends, so a reader watches Thin become Full.
export function DepthWord({ depth, gap }: { depth: Depth; gap: Gap | null }) {
  const word = describeDepth(depth);
  const tone = depthTone(depth, gap);

  if (gap === null || gap.missing === null) {
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
      <p className="signal-sentence">{gap.missing}</p>
    </details>
  );
}
