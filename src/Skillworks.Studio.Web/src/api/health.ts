import type { Part } from '../lib/health';
import { getJson } from './json';

export interface Health {
  parts: Part[];
  whyEmpty: string | null;
}

export function fetchHealth(signal?: AbortSignal): Promise<Health> {
  return getJson<Health>('/api/health', signal);
}
