import { filterQuery, type Filter } from '../../filters/lib/filters';
import { getJson } from '../../http/api/json';
import type { SkillsAnswer } from '../lib/skills';

export function fetchSkills(filter: Filter, signal: AbortSignal): Promise<SkillsAnswer> {
  return getJson<SkillsAnswer>(`/api/skills${filterQuery(filter)}`, signal);
}
