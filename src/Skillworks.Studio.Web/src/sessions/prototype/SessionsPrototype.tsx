// PROTOTYPE — throwaway. Question: how should Studio show one session, so a person can dig from a repository to a
// session and see what happened, where the time went and what was said?
// Three variants on the throwaway /prototype/sessions route, switched by ?variant= and the floating bar.
// The data is a made-up fortnight. It assumes Tempo holds the traces and that most repositories send the words.

import { useSearchParams } from 'react-router';
import { DrillVariant } from './drill/DrillVariant';
import { DuoVariant } from './duo/DuoVariant';
import { PrototypeSwitcher, type VariantEntry } from './PrototypeSwitcher';
import { ScrubVariant } from './scrub/ScrubVariant';
import { StoryVariant } from './story/StoryVariant';
import { useSessionView } from './useSessionView';

const variants: VariantEntry[] = [
  { key: 'D', name: 'The verdict — C’s table, then B’s instrument' },
  { key: 'A', name: 'Drill — columns, dashboard, trace drawer' },
  { key: 'B', name: 'Scrub — one timeline instrument, brush and dock' },
  { key: 'C', name: 'Story — the conversation first, timeline as minimap' },
];

export function SessionsPrototype() {
  const [params] = useSearchParams();
  const variant = params.get('variant') ?? 'D';
  const view = useSessionView();

  return (
    <>
      {variant === 'A' && <DrillVariant view={view} />}
      {variant === 'B' && <ScrubVariant view={view} />}
      {variant === 'C' && <StoryVariant view={view} />}
      {variant === 'D' && <DuoVariant view={view} />}
      <PrototypeSwitcher variants={variants} />
    </>
  );
}
