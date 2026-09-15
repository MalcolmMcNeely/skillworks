import { describeMoment } from '../../moments/lib/moments';

export interface Origin {
  trigger: string | null;
  source: string | null;
  plugin: string | null;
  marketplace: string | null;
}

// Every gap arrives as an empty list of origins, so only this word tells a screen which it is.
export type ProvenanceGap =
  | 'complete'
  | 'unreachable'
  | 'truncated'
  | 'telemetryOff'
  | 'telemetryUnknown'
  | 'quiet';

export interface Provenance {
  gap: ProvenanceGap;
  missing: string | null;
  sinceUtc: string;
}

// Words, not a dash: a dash reads as a fact about the skill, not a gap in what the store recorded.
const unrecorded = 'Not recorded';

const triggers: Record<string, string> = {
  'claude-proactive': 'Claude chose it',
  'user-slash': 'A developer typed it',
  'nested-skill': 'Another skill called it',
  'agent-preload': 'An agent was given it',
};

export function describeTrigger(trigger: string | null): string {
  return trigger === null ? unrecorded : (triggers[trigger] ?? trigger);
}

export function describeDelivery(origin: Origin): string {
  if (origin.plugin === null) {
    return origin.source ?? unrecorded;
  }

  return origin.marketplace === null ? origin.plugin : `${origin.plugin} from ${origin.marketplace}`;
}

export function describeTriggers(origins: readonly Origin[]): string {
  return join(origins.map((origin) => describeTrigger(origin.trigger)));
}

// Two skills that share a name read as two here, which is the only place the difference shows.
export function describeDeliveries(origins: readonly Origin[]): string {
  return join(origins.map(describeDelivery));
}

// Not telemetry off: it speaks for this machine only, so the store may still hold events a filter left out.
export function explainsEmpty(gap: ProvenanceGap): boolean {
  return gap === 'unreachable' || gap === 'quiet' || gap === 'telemetryUnknown';
}

export function describeProvenance(provenance: Provenance): string {
  return (
    provenance.missing ??
    `Where a skill came from is known for events since ${describeMoment(provenance.sinceUtc)}.`
  );
}

function join(described: readonly string[]): string {
  const distinct = [...new Set(described)];

  return distinct.length === 0 ? unrecorded : distinct.join(', ');
}
