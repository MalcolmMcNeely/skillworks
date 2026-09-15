import { filterQuery, type Filter, type Span } from '../../filters/lib/filters';
import type { Gap } from '../../gaps/lib/gaps';
import { getJson } from '../../http/api/json';
import type { Origin } from '../../provenance/lib/provenance';

export interface Activation {
  id: string;
  skill: string;
  sessionId: string | null;
  repository: string | null;
  timestampUtc: string;
  origin: Origin;
}

export interface ActivationList {
  activations: Activation[];
  gap: Gap;
  span: Span;
}

export interface ActivationOpened {
  // Null only when the events store could not be read, and the Gap says why.
  activation: Activation | null;
  gap: Gap;
}

export function fetchActivations(filter: Filter, signal: AbortSignal): Promise<ActivationList> {
  return getJson<ActivationList>(`/api/activations${filterQuery(filter)}`, signal);
}

export function fetchActivation(id: string, signal: AbortSignal): Promise<ActivationOpened> {
  return getJson<ActivationOpened>(`/api/activations/${encodeURIComponent(id)}`, signal);
}
