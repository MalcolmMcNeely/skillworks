import { filterQuery, type Filter } from '../lib/filters';
import type { TokenSplit } from '../lib/skills';
import { getJson } from './json';

/** What a skill cost, split by kind so an expensive one can be diagnosed rather than just noticed. */
export interface SkillSpend extends TokenSplit {
  /** Already inside `outputTokens`, because that is how thinking is billed. */
  thinkingTokens: number;
  /** US dollars, worked out by the API from its price table at the moment of the question. */
  cost: number;
  /** True when some tokens ran on a model with no price, so the money is a floor. */
  costIsPartial: boolean;
}

/** One row of `GET /api/skills`, already shaped by the API. */
export interface SkillSummary {
  name: string;
  activations: number;
  repositories: string[];
  branches: string[];
  models: string[];
  efforts: string[];
  spend: SkillSpend;
  averageCost: number;
}

/** The filter goes to the API, never to the rows that come back: narrowing happens in the query. */
export function fetchSkills(filter: Filter, signal: AbortSignal): Promise<SkillSummary[]> {
  return getJson<SkillSummary[]>(`/api/skills${filterQuery(filter)}`, signal);
}
