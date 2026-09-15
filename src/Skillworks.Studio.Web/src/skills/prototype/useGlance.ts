// PROTOTYPE — throwaway. Everything a variant reads, in one object, so a variant is only rendering.

import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { fetchActivations, type ActivationList } from '../../activations/api/activations';
import { activationsPath } from '../../activations/lib/activations';
import { fetchFilters } from '../../filters/api/filters';
import { readFilter, withChosen, type Filter } from '../../filters/lib/filters';
import type { Health } from '../../health/api/health';
import { useHealth } from '../../health/components/useHealth';
import { describeFetchFailure } from '../../http/lib/errors';
import { fetchTelemetry, type TelemetryState } from '../../telemetry/api/telemetry';
import type { SkillTable } from '../api/skills';
import { spanChoiceOf, withSpan, type SpanChoice } from './glance';

export interface Glance {
  skills: SkillTable | null;
  skillsError: string | null;
  // True while the answer on screen is for an older filter than the one asked for.
  pending: boolean;
  activations: ActivationList | null;
  health: Health | null;
  healthFailure: string | null;
  recheck: () => void;
  telemetry: TelemetryState | null;
  // Stubbed: flips in memory only, so trying a variant never writes the developer's settings file.
  flipTelemetry: (emitting: boolean) => void;
  filter: Filter;
  span: SpanChoice;
  chooseSpan: (choice: Exclude<SpanChoice, 'custom'>) => void;
  repositories: string[];
  chooseRepository: (repository: string) => void;
  openSkill: (skill: string) => void;
}

export function useGlance(
  skills: SkillTable | null,
  skillsError: string | null,
  pending: boolean,
  onFilter: (filter: Filter) => void,
): Glance {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const filter = readFilter(params);
  const narrowing = `${filter.from}|${filter.to}|${filter.repository}|${filter.skill}`;

  const [activations, setActivations] = useState<ActivationList | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryState | null>(null);
  const [repositories, setRepositories] = useState<string[]>([]);
  const { report, failure, recheck } = useHealth();

  useEffect(() => {
    const abort = new AbortController();
    const [from, to, repository, skill] = narrowing.split('|');

    fetchActivations({ from, to, repository, skill }, abort.signal).then(setActivations, (problem: unknown) => {
      if (!abort.signal.aborted) {
        console.warn(describeFetchFailure(problem));
      }
    });

    return () => abort.abort();
  }, [narrowing]);

  useEffect(() => {
    const abort = new AbortController();

    fetchTelemetry(abort.signal).then(setTelemetry, () => undefined);
    fetchFilters(abort.signal).then((choices) => setRepositories(choices.repositories), () => undefined);

    return () => abort.abort();
  }, []);

  return {
    skills,
    skillsError,
    pending,
    activations,
    health: report,
    healthFailure: failure,
    recheck,
    telemetry,
    flipTelemetry: (emitting) => setTelemetry((state) => (state === null ? state : { ...state, emitting })),
    filter,
    span: spanChoiceOf(filter),
    chooseSpan: (choice) => onFilter(withSpan(filter, choice)),
    repositories: withChosen(repositories, filter.repository),
    chooseRepository: (repository) => onFilter({ ...filter, repository }),
    openSkill: (skill) => navigate(activationsPath(params.toString(), skill)),
  };
}
