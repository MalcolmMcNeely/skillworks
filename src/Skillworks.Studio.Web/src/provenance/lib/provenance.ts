export interface Origin {
  trigger: string | null;
  source: string | null;
  plugin: string | null;
  marketplace: string | null;
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

function join(described: readonly string[]): string {
  const distinct = [...new Set(described)];

  return distinct.length === 0 ? unrecorded : distinct.join(', ');
}
