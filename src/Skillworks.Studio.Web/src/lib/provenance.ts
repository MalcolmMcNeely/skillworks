import { describeMoment } from './activations';

/**
 * How provenance reads as words. The API hands back what the events store recorded, verbatim, and
 * the sentences are made here — so this module stays structural and never imports the wire types.
 */

/** One way a skill was delivered and set off. */
export interface Origin {
  trigger: string | null;
  source: string | null;
  plugin: string | null;
  marketplace: string | null;
}

/**
 * Which way provenance fell short, if it did. Every one of these arrives as an empty list of
 * origins, so the word is the only thing that tells a screen what it is looking at.
 */
export type ProvenanceGap =
  | 'complete'
  | 'unreachable'
  | 'truncated'
  | 'telemetryOff'
  | 'telemetryUnknown'
  | 'quiet';

/** What the events store had to say about the period on screen. */
export interface Provenance {
  gap: ProvenanceGap;
  missing: string | null;
  sinceUtc: string;
}

/**
 * Nothing recorded, said in words. A dash would read as a fact about the skill, and what this
 * column is missing is the store's answer rather than the skill's history.
 */
const unrecorded = 'Not recorded';

/** The four the store spells. Anything else is shown as it arrived rather than dropped. */
const triggers: Record<string, string> = {
  'claude-proactive': 'Claude chose it',
  'user-slash': 'A developer typed it',
  'nested-skill': 'Another skill called it',
  'agent-preload': 'An agent was given it',
};

/** What set one firing off: the model reaching for a skill, or a developer asking for it. */
export function describeTrigger(trigger: string | null): string {
  return trigger === null ? unrecorded : (triggers[trigger] ?? trigger);
}

/**
 * Where a skill was delivered from: the plugin and the marketplace behind it, or the place it was
 * loaded out of when no plugin delivered it.
 */
export function describeDelivery(origin: Origin): string {
  if (origin.plugin === null) {
    return origin.source ?? unrecorded;
  }

  return origin.marketplace === null ? origin.plugin : `${origin.plugin} from ${origin.marketplace}`;
}

/** Every trigger one skill was set off by, in one cell. */
export function describeTriggers(origins: readonly Origin[]): string {
  return join(origins.map((origin) => describeTrigger(origin.trigger)));
}

/**
 * Every way one skill name was delivered, in one cell. Two names that are really two skills read
 * as two here, which is the only place the difference shows.
 */
export function describeDeliveries(origins: readonly Origin[]): string {
  return join(origins.map(describeDelivery));
}

/**
 * What the screen says about the provenance beside it. A period the store had nothing for says so
 * in its own words, because a column read as a fact is the failure this half is prone to.
 */
export function describeProvenance(provenance: Provenance): string {
  return (
    provenance.missing ??
    `Where a skill came from is known for events since ${describeMoment(provenance.sinceUtc)}.`
  );
}

/**
 * Why one firing has no provenance beside it. The store may have been unreadable, or may simply
 * hold nothing from that moment, and a reader judging one firing needs to be told which.
 */
export function describeMissingOrigin(provenance: Provenance): string {
  return provenance.missing ?? 'The events store has nothing recorded for this firing.';
}

function join(described: readonly string[]): string {
  const distinct = [...new Set(described)];

  return distinct.length === 0 ? unrecorded : distinct.join(', ');
}
