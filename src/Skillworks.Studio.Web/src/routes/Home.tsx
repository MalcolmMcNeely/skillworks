import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { fetchSkills, type SkillTable as SkillsAnswer } from '../api/skills';
import { FilterBar } from '../components/FilterBar';
import { HealthPanel } from '../components/HealthPanel';
import { IngestPanel } from '../components/IngestPanel';
import { SkillTable } from '../components/SkillTable';
import { TelemetrySwitch } from '../components/TelemetrySwitch';
import { useHealth } from '../components/useHealth';
import { describeFetchFailure } from '../lib/errors';
import { describeEmpty, filterParams, readFilter, type Filter } from '../lib/filters';
import { describeProvenance } from '../lib/provenance';
import { readSort, withSort, type Sort } from '../lib/sorting';

export function Home() {
  const [skills, setSkills] = useState<SkillsAnswer | null>(null);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [passes, setPasses] = useState(0);

  // Read here rather than inside the panel, because the same answer does two jobs on this page: it
  // fills the panel, and it is what tells an empty table which source is missing.
  const health = useHealth();

  // The filter and the sort both live in the address bar, so a reload, a bookmark, the back button
  // and a trip out to one activation all land on the view the reader built. There is nothing to
  // save and nothing to restore.
  const [params, setParams] = useSearchParams();
  const filter = readFilter(params);
  const sort = readSort(params);

  // The same filter written out flat. `params` is a new object on every render, so an effect keyed
  // on it would re-read on every render; keyed on the text, it re-reads when the filter changes.
  const narrowing = params.toString();

  // Counting passes rather than re-reading here keeps this callback the same object for the panel's
  // whole life, so changing a filter cannot tear the ingest poll down and start it again.
  const countPass = useCallback(() => setPasses((counted) => counted + 1), []);

  // Read again when the filter changes and when the ingest finishes a pass, so a session written a
  // moment ago reaches the table without a reload. The table keeps its own sorting across the read.
  useEffect(() => {
    const abort = new AbortController();

    // Read back out of the text rather than closed over from above, so the only thing this effect
    // depends on is the thing it is keyed on.
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

    // `passes` is a nudge rather than a value, so nothing above reads it. It is here because a
    // finished pass may have put a new session in the store, and the table should say so.
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [narrowing, passes]);

  // Replaced rather than pushed: the address bar holds the view being looked at, and a trip through
  // four filters should not cost four presses of the back button to leave.
  const narrow = (next: Filter) => setParams(withSort(filterParams(next), sort), { replace: true });

  const rank = (next: Sort) => setParams(withSort(filterParams(filter), next), { replace: true });

  return (
    <main>
      <h1>Skillworks Studio</h1>

      {/* Above the table on purpose. A reader who finds nothing below should meet the reason for it
          on the way down rather than hunt for it at the bottom of the page. */}
      <HealthPanel reading={health} />

      <FilterBar filter={filter} onChange={narrow} />

      {skillsError !== null && <p data-testid="skills-error">{skillsError}</p>}
      {skills !== null && (
        <>
          {/* Beside the table rather than inside it. What the events store could not tell us is one
              fact about the whole period, and repeating it down a column would read as many. */}
          <p data-testid="provenance-note">{describeProvenance(skills.provenance)}</p>

          {skills.skills.length === 0 ? (
            // Held back until the health read has come back one way or the other. The filter and
            // the missing source both explain an empty table, and saying the filter first and the
            // folder a moment later would let a reader act on the wrong one.
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
