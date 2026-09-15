import type { Gap } from '../lib/gaps';

// Nothing when nothing is missing, as the span shown beside it already names the days covered.
export function GapNote({ gap }: { gap: Gap }) {
  return gap.missing === null ? null : <p data-testid="gap-note">{gap.missing}</p>;
}
