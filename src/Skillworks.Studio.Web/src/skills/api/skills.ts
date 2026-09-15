import { filterQuery, type Filter, type Span } from '../../filters/lib/filters';
import { getJson } from '../../http/api/json';
import type { Origin, Provenance } from '../../provenance/lib/provenance';
import type { TokenSplit } from '../lib/skills';

export interface SkillSpend extends TokenSplit {
  // US dollars, as Claude Code estimated them.
  cost: number;
}

export interface SkillSummary {
  name: string;
  activations: number;
  repositories: string[];
  models: string[];
  efforts: string[];
  spend: SkillSpend;
  averageCost: number;
  origins: Origin[];
}

export interface SkillTable {
  skills: SkillSummary[];
  provenance: Provenance;
  span: Span;
}

export function fetchSkills(filter: Filter, signal: AbortSignal): Promise<SkillTable> {
  return getJson<SkillTable>(`/api/skills${filterQuery(filter)}`, signal);
}
