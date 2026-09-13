import { getJson } from './json';

/** One row of `GET /api/skills`, already shaped by the API. */
export interface SkillSummary {
  name: string;
  activations: number;
  repositories: string[];
  branches: string[];
}

export function fetchSkills(signal: AbortSignal): Promise<SkillSummary[]> {
  return getJson<SkillSummary[]>('/api/skills', signal);
}
