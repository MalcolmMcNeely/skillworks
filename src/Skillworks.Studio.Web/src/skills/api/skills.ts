import { filterQuery, type Filter, type Span } from '../../filters/lib/filters';
import { getJson } from '../../http/api/json';
import type { Origin, Provenance } from '../../provenance/lib/provenance';
import type { SkillSpend } from '../lib/skills';

export interface SkillSummary {
  name: string;
  activations: number;
  repositories: string[];
  // Null where the skill's Turns went unnamed, as an empty list or a zero would say it spent nothing.
  models: string[] | null;
  efforts: string[] | null;
  spend: SkillSpend | null;
  averageCost: number | null;
  origins: Origin[];
}

export interface SkillTable {
  skills: SkillSummary[];
  // Null when the filter names a skill, as some of it may not be that skill's.
  unnamedSpend: SkillSpend | null;
  provenance: Provenance;
  span: Span;
}

export function fetchSkills(filter: Filter, signal: AbortSignal): Promise<SkillTable> {
  return getJson<SkillTable>(`/api/skills${filterQuery(filter)}`, signal);
}
