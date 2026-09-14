import { getJson } from '../../fetching/api/json';
import { filterQuery, type Filter } from '../../filters/lib/filters';
import type { Origin, Provenance } from '../../provenance/lib/provenance';

export interface ActivationSummary {
  id: string;
  skill: string;
  repository: string | null;
  branch: string | null;
  model: string | null;
  effort: string | null;
  timestampUtc: string;
  // Null when no event sits near enough to this firing to be it.
  origin: Origin | null;
}

export interface ActivationArgument {
  name: string;
  value: string;
}

export interface ActivationDetail extends ActivationSummary {
  sessionId: string;
  arguments: ActivationArgument[];
}

export interface ActivationList {
  activations: ActivationSummary[];
  provenance: Provenance;
}

export interface ActivationOpened {
  activation: ActivationDetail;
  provenance: Provenance;
}

export function fetchActivations(filter: Filter, signal: AbortSignal): Promise<ActivationList> {
  return getJson<ActivationList>(`/api/activations${filterQuery(filter)}`, signal);
}

export function fetchActivation(id: string, signal: AbortSignal): Promise<ActivationOpened> {
  return getJson<ActivationOpened>(`/api/activations/${encodeURIComponent(id)}`, signal);
}
