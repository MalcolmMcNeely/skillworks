import type { Part } from '../lib/health';
import { getJson } from './json';

/** `GET /api/health`: every part of Studio, already shaped by the API. */
export interface Health {
  parts: Part[];
  /**
   * Why a view built from the transcripts has nothing in it, naming the source that is missing and
   * the action that would fix it. Null when the transcript half is healthy and an empty view is an
   * honest empty history.
   */
  whyEmpty: string | null;
}

/**
 * It probes the events store rather than remembering it, so this is a read of the outside world
 * and worth asking again after a container has been started.
 */
export function fetchHealth(signal?: AbortSignal): Promise<Health> {
  return getJson<Health>('/api/health', signal);
}
