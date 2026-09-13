import { filterQuery, type Filter } from '../lib/filters';
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
}

/** One thing a skill was called with, under the name the transcript recorded it under. */
export interface ActivationArgument {
  name: string;
  value: string;
}

/** `GET /api/activations/{id}`: one firing opened, with what it was actually asked to do. */
export interface ActivationDetail extends ActivationSummary {
  sessionId: string;
  arguments: ActivationArgument[];
}

/** The same filter the skill table asks with, so a list reached from a row counts the same slice. */
export function fetchActivations(filter: Filter, signal: AbortSignal): Promise<ActivationSummary[]> {
  return getJson<ActivationSummary[]>(`/api/activations${filterQuery(filter)}`, signal);
}

export function fetchActivation(id: string, signal: AbortSignal): Promise<ActivationDetail> {
  return getJson<ActivationDetail>(`/api/activations/${encodeURIComponent(id)}`, signal);
}
