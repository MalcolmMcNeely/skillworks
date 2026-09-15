// PROTOTYPE — throwaway. Question: what should the at-a-glance telemetry screen look like?
// Variants of Home on the existing `/` route, switched by `?variant=`. E folds the first round's feedback together.

import type { ReactNode } from 'react';
import { useSearchParams } from 'react-router';
import type { Filter } from '../../filters/lib/filters';
import type { SkillTable } from '../api/skills';
import { DeckVariant } from './DeckVariant';
import { MapVariant } from './MapVariant';
import { PrototypeSwitcher, type VariantEntry } from './PrototypeSwitcher';
import { PulseVariant } from './PulseVariant';
import { ScopeVariant } from './ScopeVariant';
import { SpendVariant } from './SpendVariant';
import { useGlance } from './useGlance';

const variants: VariantEntry[] = [
  { key: '', name: 'Today’s page' },
  { key: 'A', name: 'Deck — ranked ladder, cyan HUD' },
  { key: 'B', name: 'Scope — bubble map, phosphor CRT' },
  { key: 'C', name: 'Pulse — time lanes, light console' },
  { key: 'D', name: 'Spend — treemap, amber tactical' },
  { key: 'E', name: 'Map — D’s layout in A’s colours' },
];

export function GlancePrototype({
  current,
  skills,
  skillsError,
  pending,
  onFilter,
}: {
  current: ReactNode;
  skills: SkillTable | null;
  skillsError: string | null;
  pending: boolean;
  onFilter: (filter: Filter) => void;
}) {
  const [params] = useSearchParams();
  const variant = params.get('variant') ?? '';
  const glance = useGlance(skills, skillsError, pending, onFilter);

  return (
    <>
      {variant === '' && current}
      {variant === 'A' && <DeckVariant glance={glance} />}
      {variant === 'B' && <ScopeVariant glance={glance} />}
      {variant === 'C' && <PulseVariant glance={glance} />}
      {variant === 'D' && <SpendVariant glance={glance} />}
      {variant === 'E' && <MapVariant glance={glance} />}
      <PrototypeSwitcher variants={variants} />
    </>
  );
}
