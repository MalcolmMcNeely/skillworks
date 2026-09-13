import { filterQuery, type Filter } from '../lib/filters';
import type { Origin, Provenance } from '../lib/provenance';
import { getJson } from './json';

/** One row of `GET /api/activations`: one firing, enough of it to pick one out. */
export interface ActivationSummary {
  id: string;
  skill: string;
  repository: string | null;
  branch: string | null;
  model: string | null;
  effort: string | null;
  timestampUtc: string;
  /** Null when no event sits near enough to this firing to be it. */
  origin: Origin | null;
}

/** One thing a skill was called with, under the name the transcript recorded it under. */
export interface ActivationArgument {
  name: string;
  value: string;
}

/** One firing opened, with what it was actually asked to do. */
export interface ActivationDetail extends ActivationSummary {
  sessionId: string;
  arguments: ActivationArgument[];
}

/** `GET /api/activations`: the firings, and what the events store had to say about them. */
export interface ActivationList {
  activations: ActivationSummary[];
  provenance: Provenance;
}

/** `GET /api/activations/{id}`: one firing, beside the same note. */
export interface ActivationOpened {
  activation: ActivationDetail;
  provenance: Provenance;
}

/** The same filter the skill table asks with, so a list reached from a row counts the same slice. */
export function fetchActivations(filter: Filter, signal: AbortSignal): Promise<ActivationList> {
  return getJson<ActivationList>(`/api/activations${filterQuery(filter)}`, signal);
}

export function fetchActivation(id: string, signal: AbortSignal): Promise<ActivationOpened> {
  return getJson<ActivationOpened>(`/api/activations/${encodeURIComponent(id)}`, signal);
}
