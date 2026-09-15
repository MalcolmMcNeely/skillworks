import { filterQuery, type Filter, type Span } from '../../filters/lib/filters';
import { getJson } from '../../http/api/json';
import type { Origin, Provenance } from '../../provenance/lib/provenance';

export interface ActivationSummary {
  id: string;
  skill: string;
  sessionId: string | null;
  repository: string | null;
  timestampUtc: string;
  origin: Origin;
}

export interface ActivationList {
  activations: ActivationSummary[];
  provenance: Provenance;
  span: Span;
}

export interface ActivationOpened {
  // Null only when the events store could not be read, and the provenance says why.
  activation: ActivationSummary | null;
  provenance: Provenance;
}

export function fetchActivations(filter: Filter, signal: AbortSignal): Promise<ActivationList> {
  return getJson<ActivationList>(`/api/activations${filterQuery(filter)}`, signal);
}

export function fetchActivation(id: string, signal: AbortSignal): Promise<ActivationOpened> {
  return getJson<ActivationOpened>(`/api/activations/${encodeURIComponent(id)}`, signal);
}
