import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { FilterBar } from '../../filters/components/FilterBar';
import { describeEmpty, filterParams, readFilter, type Filter } from '../../filters/lib/filters';
import { HealthPanel } from '../../health/components/HealthPanel';
import { useHealth } from '../../health/components/useHealth';
import { describeFetchFailure } from '../../http/lib/errors';
import { IngestPanel } from '../../ingest/components/IngestPanel';
import { describeProvenance } from '../../provenance/lib/provenance';
import { TelemetrySwitch } from '../../telemetry/components/TelemetrySwitch';
import { fetchSkills, type SkillTable as SkillsAnswer } from '../api/skills';
import { SkillTable } from '../components/SkillTable';
import { readSort, withSort, type Sort } from '../lib/sorting';

export function Home() {
  const [skills, setSkills] = useState<SkillsAnswer | null>(null);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [passes, setPasses] = useState(0);

  // Read here, not in the panel, because the same answer tells an empty table which source is missing.
  const health = useHealth();

  // Filter and sort live in the address bar, so a reload, a bookmark or the back button lands on the same view.
  const [params, setParams] = useSearchParams();
  const filter = readFilter(params);
  const sort = readSort(params);

  // `params` is a new object every render, so the effect keys on its text or it would re-read every time.
  const narrowing = params.toString();

  // Counting passes keeps this callback stable, so changing a filter never restarts the ingest poll.
  const countPass = useCallback(() => setPasses((counted) => counted + 1), []);

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

    // `passes` is a nudge nothing reads: a finished pass may have put a new session in the transcript store.
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [narrowing, passes]);

  // Replaced, not pushed, so trying four filters does not cost four presses of the back button.
  const narrow = (next: Filter) => setParams(withSort(filterParams(next), sort), { replace: true });

  const rank = (next: Sort) => setParams(withSort(filterParams(filter), next), { replace: true });

  return (
    <main>
      <h1>Skillworks Studio</h1>

      {/* Above the table, so a reader who finds nothing meets the reason on the way down. */}
      <HealthPanel reading={health} />

      <FilterBar filter={filter} onChange={narrow} />

      {skillsError !== null && <p data-testid="skills-error">{skillsError}</p>}
      {skills !== null && (
        <>
          {/* Not in the table: the gap is one fact about the period, and a column would repeat it as many. */}
          <p data-testid="provenance-note">{describeProvenance(skills.provenance)}</p>

          {skills.skills.length === 0 ? (
            // Held back until health settles, or a reader may act on the filter before the missing source shows.
            health.settled && (
              <p data-testid="skills-empty">
                {describeEmpty(filter, health.report?.whyEmpty ?? null)}
              </p>
            )
          ) : (
            <SkillTable skills={skills.skills} sort={sort} onSort={rank} />
          )}
        </>
      )}

      <IngestPanel onPassFinished={countPass} />
      <TelemetrySwitch />
    </main>
  );
}
