import { filterQuery, type Filter } from '../../filters/lib/filters';
import { getJson } from '../../http/api/json';
import type { Origin, Provenance } from '../../provenance/lib/provenance';
import type { TokenSplit } from '../lib/skills';

export interface SkillSpend extends TokenSplit {
  // Already inside outputTokens, because that is how thinking is billed.
  thinkingTokens: number;
  // US dollars, priced by the API at the moment of the question.
  cost: number;
  costIsPartial: boolean;
}

export interface SkillSummary {
  name: string;
  activations: number;
  repositories: string[];
  branches: string[];
  models: string[];
  efforts: string[];
  spend: SkillSpend;
  averageCost: number;
  origins: Origin[];
}

export interface SkillTable {
  skills: SkillSummary[];
  provenance: Provenance;
}

export function fetchSkills(filter: Filter, signal: AbortSignal): Promise<SkillTable> {
  return getJson<SkillTable>(`/api/skills${filterQuery(filter)}`, signal);
}
