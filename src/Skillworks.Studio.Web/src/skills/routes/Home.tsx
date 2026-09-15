import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { FilterBar } from '../../filters/components/FilterBar';
import { describeEmpty, describeSpan, filterParams, readFilter, type Filter } from '../../filters/lib/filters';
import { GapNote } from '../../gaps/components/GapNote';
import { explainsEmpty } from '../../gaps/lib/gaps';
import { HealthPanel } from '../../health/components/HealthPanel';
import { describeFetchFailure } from '../../http/lib/errors';
import { TelemetrySwitch } from '../../telemetry/components/TelemetrySwitch';
import { fetchSkills, type SkillTable as SkillsAnswer } from '../api/skills';
import { SkillTable } from '../components/SkillTable';
import { describeUnnamedSpend } from '../lib/skills';
import { readSort, withSort, type Sort } from '../lib/sorting';

export function Home() {
  const [skills, setSkills] = useState<SkillsAnswer | null>(null);
  const [skillsError, setSkillsError] = useState<string | null>(null);

  // Filter and sort live in the address bar, so a reload, a bookmark or the back button lands on the same view.
  const [params, setParams] = useSearchParams();
  const filter = readFilter(params);
  const sort = readSort(params);

  // Text, as a filter object is new every render; the sort is left out as it needs no new answer.
  const narrowing = filterParams(filter).toString();

  useEffect(() => {
    const abort = new AbortController();

    // Read back out of the text, so the effect depends only on what it is keyed on.
    fetchSkills(readFilter(new URLSearchParams(narrowing)), abort.signal)
      .then((next) => {
        setSkills(next);
        setSkillsError(null);
      })
      .catch((failure: unknown) => {
        // An abort is the page tidying up after itself, not a failure worth showing.
        if (!abort.signal.aborted) {
          setSkillsError(describeFetchFailure(failure));
        }
      });

    return () => abort.abort();
  }, [narrowing]);

  // Replaced, not pushed, so trying four filters does not cost four presses of the back button.
  const narrow = (next: Filter) => setParams(withSort(filterParams(next), sort), { replace: true });

  const rank = (next: Sort) => setParams(withSort(filterParams(filter), next), { replace: true });

  return (
    <main>
      <h1>Skillworks Studio</h1>

      <HealthPanel />

      <FilterBar filter={filter} onChange={narrow} />

      {skillsError !== null && <p data-testid="skills-error">{skillsError}</p>}
      {skills !== null && (
        <>
          {/* From the answer, not the filter, so the words name the days the API actually counted. */}
          <p data-testid="skills-span">Covers {describeSpan(skills.span)}.</p>

          {/* Not in the table: the gap is one fact about the period, and a column would repeat it as many. */}
          <GapNote gap={skills.gap} />

          {/* Not a row: no skill is named for it, and a row would read as a skill. */}
          {skills.unnamedSpend !== null && (
            <p data-testid="unnamed-spend">{describeUnnamedSpend(skills.unnamedSpend)}</p>
          )}

          {skills.skills.length === 0 ? (
            !explainsEmpty(skills.gap.kind) && (
              <p data-testid="skills-empty">{describeEmpty(filter)}</p>
            )
          ) : (
            <SkillTable skills={skills.skills} sort={sort} onSort={rank} />
          )}
        </>
      )}

      <TelemetrySwitch />
    </main>
  );
}
