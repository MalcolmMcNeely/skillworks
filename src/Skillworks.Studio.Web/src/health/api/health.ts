import { getJson } from '../../http/api/json';
import type { Part } from '../lib/health';

export interface Health {
  parts: Part[];
}

export function fetchHealth(signal?: AbortSignal): Promise<Health> {
  return getJson<Health>('/api/health', signal);
}
