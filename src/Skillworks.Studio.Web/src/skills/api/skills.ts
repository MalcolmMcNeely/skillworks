import { filterQuery, type Filter } from '../../shared/filters/lib/filters';
import { getLines } from '../../shared/http/api/json';
import type { SkillsLine } from '../lib/skills';

export function fetchSkills(filter: Filter, signal: AbortSignal): AsyncGenerator<SkillsLine> {
  return getLines<SkillsLine>(`/api/skills${filterQuery(filter)}`, signal);
}
