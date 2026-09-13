/** One row of `GET /api/skills`, already shaped by the API. */
export interface SkillSummary {
  name: string;
  activations: number;
  repositories: string[];
  branches: string[];
}

export async function fetchSkills(signal: AbortSignal): Promise<SkillSummary[]> {
  const response = await fetch('/api/skills', { signal });

  if (!response.ok) {
    throw new Error(`GET /api/skills returned ${response.status}`);
  }

  return (await response.json()) as SkillSummary[];
}
